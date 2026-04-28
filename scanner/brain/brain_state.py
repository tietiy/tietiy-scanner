"""Brain state — single write chokepoint for output/brain/*.json.

Atomic write (tmp + os.rename) + schema_version stamp + as_of_date
indexed history archives at output/brain/history/<as_of_date>_<view>.json.

Per locked Step 3 design (K-4): FULL RETENTION, NO PRUNE. History
archives accumulate indefinitely. Disk-space cleanup deferred to
Wave 6+ infrastructure if ever needed.

Cross-day comparison primitives (P-7): list_brain_archives() and
load_brain_archive() ship in Step 3 even though Step 3 doesn't call
them. Step 5 LLM gates need them.

See doc/brain_design_v1.md §2 (single chokepoint) + §4 Step 3.
Mirrors scanner/bridge/core/state_writer.py atomic-write pattern.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional


_BRAIN_SCHEMA_VERSION = 1
_BRAIN_DIRNAME = "brain"
_HISTORY_DIRNAME = "history"
_ARCHIVE_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)\.json$")
_IST = timezone(timedelta(hours=5, minutes=30))


def write_brain_artifact(name: str, data: dict,
                         output_dir: str = "output") -> dict:
    """
    Atomically writes output/brain/<name>.json (current snapshot)
    + output/brain/history/<as_of_date>_<name>.json (dated archive).

    Stamps schema_version=1, view_name, generated_at if not present.
    Caller MUST provide data['as_of_date'] (raises ValueError otherwise).

    Returns {"current_path", "history_path", "bytes_written"}.

    Per K-4: NO PRUNE. History accumulates.
    Per N-2: Last-write-wins (idempotent runs make collision a no-op).
    """
    if "as_of_date" not in data:
        raise ValueError(
            f"data dict for view {name!r} missing required "
            f"'as_of_date' field; brain_state cannot index history archive")

    data.setdefault("schema_version", _BRAIN_SCHEMA_VERSION)
    data.setdefault("view_name", name)
    data["generated_at"] = datetime.now(_IST).isoformat()

    brain_dir = os.path.join(output_dir, _BRAIN_DIRNAME)
    history_dir = os.path.join(brain_dir, _HISTORY_DIRNAME)
    os.makedirs(history_dir, exist_ok=True)

    payload = json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False)

    current_path = os.path.join(brain_dir, f"{name}.json")
    history_path = os.path.join(history_dir,
                                f"{data['as_of_date']}_{name}.json")

    bytes_current = _atomic_write(current_path, payload)
    bytes_history = _atomic_write(history_path, payload)

    return {
        "current_path": current_path,
        "history_path": history_path,
        "bytes_written": bytes_current + bytes_history,
    }


def list_brain_archives(view_name: str,
                        output_dir: str = "output") -> list[str]:
    """
    Returns sorted list of as_of_date strings for which <view>.json
    archives exist. P-7 primitive for Step 5+ cross-day comparison.
    """
    history_dir = os.path.join(output_dir, _BRAIN_DIRNAME, _HISTORY_DIRNAME)
    if not os.path.isdir(history_dir):
        return []
    dates = []
    for fname in os.listdir(history_dir):
        m = _ARCHIVE_NAME_RE.match(fname)
        if m and m.group(2) == view_name:
            dates.append(m.group(1))
    return sorted(dates)


def load_brain_archive(view_name: str, date_iso: str,
                       output_dir: str = "output") -> Optional[dict]:
    """
    Returns archive dict for that date, or None if not found. Logs warn
    on schema_version mismatch but still returns the dict.
    """
    path = os.path.join(output_dir, _BRAIN_DIRNAME, _HISTORY_DIRNAME,
                        f"{date_iso}_{view_name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("schema_version") != _BRAIN_SCHEMA_VERSION:
        import sys
        print(f"[brain_state] WARNING: archive {path} has "
              f"schema_version={data.get('schema_version')!r}; "
              f"expected {_BRAIN_SCHEMA_VERSION}; degraded fallback",
              file=sys.stderr)
    return data


def _atomic_write(target_path: str, content: str) -> int:
    """Mirrors scanner/bridge/core/state_writer.py:_atomic_write pattern.

    Writes to sibling tmp file, fsyncs, then os.rename. Tmp suffix
    includes pid so cross-process writes never collide.
    """
    parent = os.path.dirname(target_path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp_path = f"{target_path}.{os.getpid()}.tmp"
    encoded = content.encode("utf-8")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        n = os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp_path, target_path)
    return n
