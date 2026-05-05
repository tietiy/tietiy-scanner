"""shadow_ops/journal.py — JSONL writer + reader for shadow ops events.

Append-only logs with event_id uniqueness, atomic appends (POSIX O_APPEND on
sub-PIPE_BUF lines), and tamper-evidence sidecars.

File layout per run directory:
  scan_events.jsonl            + scan_events.jsonl.checksum
  candidate_signals.jsonl      + candidate_signals.jsonl.checksum
  trade_cards.jsonl            + trade_cards.jsonl.checksum
  lifecycle_events.jsonl       + lifecycle_events.jsonl.checksum
  fill_simulations.jsonl       + fill_simulations.jsonl.checksum

The trade_cards.jsonl is treated identically to other event logs in Step 3
(append-only, event_id-unique on TradeCard creation). The materialization
logic (regenerate trade_cards.jsonl from lifecycle_events.jsonl as a derived
read-model per architecture doc §3.3.3) lands in Step 7.

POSIX-only: relies on fcntl.flock and POSIX append atomicity. macOS + Linux only.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Type

from shadow_ops.schemas import (
    Event,
    ScanEvent,
    CandidateSignal,
    TradeCard,
    LifecycleEvent,
    FillSimulation,
)


# ============================================================
# Errors
# ============================================================

class JournalError(Exception):
    """Base class for journal errors."""
    pass


class DuplicateEventIdError(JournalError):
    pass


class ChecksumMismatchError(JournalError):
    pass


class InvalidJsonlError(JournalError):
    pass


# ============================================================
# Constants
# ============================================================

EVENT_CLASS_TO_FILENAME: Dict[Type[Event], str] = {
    ScanEvent: "scan_events.jsonl",
    CandidateSignal: "candidate_signals.jsonl",
    TradeCard: "trade_cards.jsonl",
    LifecycleEvent: "lifecycle_events.jsonl",
    FillSimulation: "fill_simulations.jsonl",
}


# ============================================================
# Helpers
# ============================================================

def _file_sha256(path: Path) -> str:
    """SHA-256 hex digest of file contents. Empty/missing file → known empty-string hash."""
    if not path.exists():
        return hashlib.sha256(b"").hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def _flock_exclusive(path: Path):
    """Acquire POSIX exclusive lock on path. Creates the file if missing.
    Releases lock on context exit. Defensive against concurrent process accidents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


# ============================================================
# JournalWriter
# ============================================================

class JournalWriter:
    """Append-only JSONL writer with event_id uniqueness, atomic appends, and
    tamper-evidence checksums.

    Single-process design. Single-writer per run_dir assumed. flock is a
    defense against operator-error parallel runs.
    """

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        # Per-file event_id cache (lazy-loaded on first access)
        self._id_cache: Dict[str, set] = {}

    # --- File path helpers ---
    def _file_for_class(self, event_class: Type[Event]) -> Path:
        if event_class not in EVENT_CLASS_TO_FILENAME:
            raise JournalError(f"no JSONL file mapping for {event_class.__name__}")
        return self.run_dir / EVENT_CLASS_TO_FILENAME[event_class]

    def _checksum_path(self, jsonl_path: Path) -> Path:
        return Path(str(jsonl_path) + ".checksum")

    def _id_cache_key(self, jsonl_path: Path) -> str:
        return str(jsonl_path)

    # --- ID cache management ---
    def _load_id_cache(self, jsonl_path: Path) -> set:
        ids: set = set()
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line_no, raw in enumerate(f, 1):
                    line = raw.rstrip("\n")
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError as e:
                        raise InvalidJsonlError(f"{jsonl_path}:{line_no}: {e}") from e
                    eid = d.get("event_id")
                    if eid:
                        ids.add(eid)
        self._id_cache[self._id_cache_key(jsonl_path)] = ids
        return ids

    def _get_id_cache(self, jsonl_path: Path) -> set:
        key = self._id_cache_key(jsonl_path)
        if key not in self._id_cache:
            return self._load_id_cache(jsonl_path)
        return self._id_cache[key]

    # --- Checksum ---
    def _verify_or_init_checksum(self, jsonl_path: Path) -> None:
        ck_path = self._checksum_path(jsonl_path)
        actual = _file_sha256(jsonl_path)
        if ck_path.exists():
            expected = ck_path.read_text().strip()
            if expected != actual:
                raise ChecksumMismatchError(
                    f"checksum mismatch for {jsonl_path}: "
                    f"expected={expected[:16]}..., actual={actual[:16]}..."
                )
        # Sidecar missing or matches: initialize/refresh
        ck_path.parent.mkdir(parents=True, exist_ok=True)
        ck_path.write_text(actual)

    def _update_checksum(self, jsonl_path: Path) -> None:
        ck_path = self._checksum_path(jsonl_path)
        ck_path.write_text(_file_sha256(jsonl_path))

    # --- Public API ---
    def write_event(self, event: Event) -> None:
        """Append an event to its corresponding JSONL file.

        Raises:
          DuplicateEventIdError — event_id already in this file
          ChecksumMismatchError — file modified outside this writer
          ValidationError       — event fails validation (re-checked here)
          InvalidJsonlError     — existing file has malformed lines
        """
        # Defense in depth: re-validate at write time. validate() is idempotent.
        event.validate()
        jsonl_path = self._file_for_class(type(event))

        with _flock_exclusive(jsonl_path):
            # 1. Verify checksum (or initialize on first write)
            self._verify_or_init_checksum(jsonl_path)
            # 2. Check uniqueness
            ids = self._get_id_cache(jsonl_path)
            if event.event_id in ids:
                raise DuplicateEventIdError(
                    f"event_id {event.event_id!r} already exists in {jsonl_path}"
                )
            # 3. Append (POSIX O_APPEND atomicity for sub-PIPE_BUF lines)
            line = event.to_json_line() + "\n"
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            # 4. Update cache + checksum
            ids.add(event.event_id)
            self._update_checksum(jsonl_path)

    # --- Read forwarding (delegate to JournalReader for clean separation) ---
    def read_events(self, event_class: Type[Event]) -> List[Event]:
        return JournalReader(self.run_dir).read_events(event_class)

    def find_event(self, event_id: str, event_class: Type[Event]) -> Optional[Event]:
        return JournalReader(self.run_dir).find_event(event_id, event_class)


# ============================================================
# JournalReader
# ============================================================

class JournalReader:
    """Read-only access to a run directory's events. Used by tests, end-of-shadow
    analysis, and the materialized-read-model regenerator (Step 7).

    Reader does NOT verify checksums — that's writer-side defense. Reader is
    permissive; if the file has been tampered with, the writer catches it on
    the next write.
    """

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)

    def _file_for_class(self, event_class: Type[Event]) -> Path:
        if event_class not in EVENT_CLASS_TO_FILENAME:
            raise JournalError(f"no JSONL file mapping for {event_class.__name__}")
        return self.run_dir / EVENT_CLASS_TO_FILENAME[event_class]

    def read_events(self, event_class: Type[Event]) -> List[Event]:
        jsonl_path = self._file_for_class(event_class)
        if not jsonl_path.exists():
            return []
        events: List[Event] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_no, raw in enumerate(f, 1):
                line = raw.rstrip("\n")
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError as e:
                    raise InvalidJsonlError(f"{jsonl_path}:{line_no}: {e}") from e
                events.append(Event.dispatch_from_dict(d))
        return events

    def find_event(self, event_id: str, event_class: Type[Event]) -> Optional[Event]:
        for ev in self.read_events(event_class):
            if ev.event_id == event_id:
                return ev
        return None

    # Convenience accessors per event type
    def all_scan_events(self) -> List[ScanEvent]:
        return self.read_events(ScanEvent)  # type: ignore[return-value]

    def all_candidate_signals(self) -> List[CandidateSignal]:
        return self.read_events(CandidateSignal)  # type: ignore[return-value]

    def all_trade_cards(self) -> List[TradeCard]:
        return self.read_events(TradeCard)  # type: ignore[return-value]

    def all_lifecycle_events(self) -> List[LifecycleEvent]:
        return self.read_events(LifecycleEvent)  # type: ignore[return-value]

    def all_fill_simulations(self) -> List[FillSimulation]:
        return self.read_events(FillSimulation)  # type: ignore[return-value]

    def trade_card_history(self, card_id: str) -> List[LifecycleEvent]:
        """All LifecycleEvents for a given card_id, in write order."""
        return [e for e in self.all_lifecycle_events() if e.card_id == card_id]

    def latest_trade_card_state(self, card_id: str) -> str:
        """Derive current state from lifecycle event log. Returns the to_state of
        the most recent lifecycle event for this card.

        Raises KeyError if no events found for card_id.
        """
        history = self.trade_card_history(card_id)
        if not history:
            raise KeyError(f"no lifecycle events for card_id={card_id!r}")
        return history[-1].to_state
