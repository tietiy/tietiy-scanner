"""shadow_ops/schemas.py — Event dataclasses for shadow ops v1.

Per architecture doc §3.3: 5 event types form the audit trail of every shadow
run. Each event has a unique event_id and is append-only via journal.py.

Validation runs in __post_init__ at construction time. Serialization is
dataclasses.asdict() + json.dumps(sort_keys=True) for byte-stable output across
diffs (§7.3 git audit trail).

Schema version: v1. Add new fields with sensible defaults; never remove or
rename existing fields without a schema-version bump.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime, date
from typing import Any, ClassVar, Dict, List, Optional, Type


# ============================================================
# Allowed-value enums (validation)
# ============================================================

VALID_REGIMES = {"Bull", "Bear", "Choppy"}
VALID_SCAN_STATUS = {"OK", "PARTIAL", "ERROR"}
VALID_TRADE_CARD_STATES = {
    "PROPOSED", "ACTIVE",
    "HYPOTHETICAL_FILLED", "HYPOTHETICAL_STOPPED",
    "NO_FILL", "EXPIRED", "SKIPPED",
}
VALID_TRIGGER_DISPOSITIONS = {
    "TRADE_CARD_PROPOSED", "SUPPRESSED_BY_KILL_001",
    "RULE_031_OVERLAY_ONLY", "NO_ACTION",
}
VALID_FILL_ATTEMPT_TYPES = {"ENTRY", "STOP", "TARGET", "EXPIRY"}
VALID_FILL_DECISIONS = {"FILLED", "NOT_FILLED", "ERROR"}

CURRENT_SCHEMA_VERSION = "v1"
MAX_EVENT_ID_LEN = 200


# ============================================================
# Validation
# ============================================================

class ValidationError(ValueError):
    """Raised when an event fails schema validation."""
    pass


def _check_non_empty_str(name: str, value: Any, max_len: int = 1000) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{name} must be non-empty string, got {type(value).__name__}={value!r}")
    if len(value) > max_len:
        raise ValidationError(f"{name} exceeds max length {max_len} ({len(value)})")


def _check_iso_timestamp(name: str, value: str) -> None:
    try:
        datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{name} must be ISO 8601 timestamp, got {value!r}")


def _check_iso_date(name: str, value: str) -> None:
    try:
        date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{name} must be YYYY-MM-DD date string, got {value!r}")


def _check_in_set(name: str, value: Any, allowed: set) -> None:
    if value not in allowed:
        raise ValidationError(f"{name}={value!r} not in allowed values {sorted(allowed)}")


# ============================================================
# Base Event
# ============================================================

@dataclass
class Event:
    """Base class for all shadow ops events.

    Subclasses set `_event_type_value` ClassVar (string discriminator) and override
    `validate()` (calling super().validate() first).
    """
    event_id: str
    event_type: str               # discriminator; must match subclass _event_type_value
    timestamp_utc: str
    event_schema_version: str = CURRENT_SCHEMA_VERSION

    # Class-level discriminator. ClassVar excludes from dataclass field machinery —
    # not in __init__, not in fields(), not in asdict().
    _event_type_value: ClassVar[str] = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Run all validation checks. Idempotent — re-callable without side effects.
        Subclasses override and call super().validate() first."""
        _check_non_empty_str("event_id", self.event_id, max_len=MAX_EVENT_ID_LEN)
        _check_non_empty_str("event_type", self.event_type)
        _check_iso_timestamp("timestamp_utc", self.timestamp_utc)
        _check_non_empty_str("event_schema_version", self.event_schema_version)
        if self._event_type_value and self.event_type != self._event_type_value:
            raise ValidationError(
                f"event_type mismatch: got {self.event_type!r}, "
                f"expected {self._event_type_value!r} for {self.__class__.__name__}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict. ClassVar fields excluded by dataclasses.asdict."""
        return asdict(self)

    def to_json_line(self) -> str:
        """Serialize to single-line JSON for JSONL append. sort_keys=True for diff-
        stable output across git commits (§7.3 audit trail)."""
        return json.dumps(
            self.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
            default=_json_default,
        )

    @classmethod
    def from_json_line(cls, line: str) -> "Event":
        return Event.dispatch_from_dict(json.loads(line))

    @staticmethod
    def dispatch_from_dict(d: Dict[str, Any]) -> "Event":
        """Polymorphic constructor: routes to subclass based on event_type discriminator.

        Forward-compat: drops fields not present on the target dataclass, so
        future schema additions don't break older readers.
        """
        et = d.get("event_type")
        klass = _EVENT_TYPE_REGISTRY.get(et)
        if klass is None:
            raise ValidationError(f"unknown event_type: {et!r}")
        valid_keys = {f.name for f in fields(klass)}
        clean = {k: v for k, v in d.items() if k in valid_keys}
        return klass(**clean)


def _json_default(o: Any) -> Any:
    """Strict JSON encoder default — raises on unexpected types so we don't silently coerce."""
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(f"non-JSON-serializable type {type(o).__name__}: {o!r}")


# ============================================================
# 5 event subclasses
# ============================================================

@dataclass
class ScanEvent(Event):
    scan_date: str = ""
    regime: str = ""
    sub_regime: Optional[str] = None
    sub_regime_inputs: Dict[str, Any] = field(default_factory=dict)
    n_signals_universe: int = 0
    n_signals_post_filter: int = 0
    scan_status: str = ""
    scan_duration_ms: int = 0
    git_commit_sha: str = ""
    data_versions: Dict[str, Any] = field(default_factory=dict)

    _event_type_value: ClassVar[str] = "scan_event"

    def validate(self) -> None:
        super().validate()
        _check_iso_date("scan_date", self.scan_date)
        _check_in_set("regime", self.regime, VALID_REGIMES)
        _check_in_set("scan_status", self.scan_status, VALID_SCAN_STATUS)
        _check_non_empty_str("git_commit_sha", self.git_commit_sha)
        if not isinstance(self.sub_regime_inputs, dict):
            raise ValidationError("sub_regime_inputs must be dict")
        if not isinstance(self.data_versions, dict):
            raise ValidationError("data_versions must be dict")
        if self.n_signals_universe < 0 or self.n_signals_post_filter < 0:
            raise ValidationError("n_signals counts must be non-negative")
        if self.scan_duration_ms < 0:
            raise ValidationError("scan_duration_ms must be non-negative")


@dataclass
class CandidateSignal(Event):
    scan_event_id: str = ""
    scan_date: str = ""
    symbol: str = ""
    sector: str = ""
    signal: str = ""
    regime: str = ""
    sub_regime: Optional[str] = None
    rule_019_match: bool = False
    rule_031_match: bool = False
    kill_001_match: bool = False
    trigger_disposition: str = ""
    rule_features_snapshot: Dict[str, Any] = field(default_factory=dict)

    _event_type_value: ClassVar[str] = "candidate_signal"

    def validate(self) -> None:
        super().validate()
        _check_non_empty_str("scan_event_id", self.scan_event_id)
        _check_iso_date("scan_date", self.scan_date)
        _check_non_empty_str("symbol", self.symbol)
        _check_non_empty_str("sector", self.sector)
        _check_non_empty_str("signal", self.signal)
        _check_in_set("regime", self.regime, VALID_REGIMES)
        _check_in_set("trigger_disposition", self.trigger_disposition, VALID_TRIGGER_DISPOSITIONS)
        if not isinstance(self.rule_features_snapshot, dict):
            raise ValidationError("rule_features_snapshot must be dict")


@dataclass
class TradeCard(Event):
    card_id: str = ""
    scan_event_id: str = ""
    candidate_signal_id: str = ""
    symbol: str = ""
    sector: str = ""
    rule_id: str = ""
    rule_031_confirm: int = 0
    kill_001_match: bool = False
    scan_date: str = ""
    proposed_entry_price: float = 0.0
    proposed_stop: float = 0.0
    proposed_target: float = 0.0
    atr: float = 0.0
    current_state: str = ""
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    actual_entry_date: Optional[str] = None
    actual_entry_price: Optional[float] = None
    actual_exit_date: Optional[str] = None
    actual_exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_pnl_pct: Optional[float] = None
    realized_R: Optional[float] = None

    _event_type_value: ClassVar[str] = "trade_card"

    def validate(self) -> None:
        super().validate()
        _check_non_empty_str("card_id", self.card_id)
        _check_non_empty_str("scan_event_id", self.scan_event_id)
        _check_non_empty_str("candidate_signal_id", self.candidate_signal_id)
        _check_non_empty_str("symbol", self.symbol)
        _check_non_empty_str("rule_id", self.rule_id)
        _check_iso_date("scan_date", self.scan_date)
        _check_in_set("current_state", self.current_state, VALID_TRADE_CARD_STATES)
        if self.rule_031_confirm not in (0, 1):
            raise ValidationError(f"rule_031_confirm must be 0 or 1, got {self.rule_031_confirm!r}")
        if self.actual_entry_date is not None:
            _check_iso_date("actual_entry_date", self.actual_entry_date)
        if self.actual_exit_date is not None:
            _check_iso_date("actual_exit_date", self.actual_exit_date)


@dataclass
class LifecycleEvent(Event):
    card_id: str = ""
    from_state: str = ""
    to_state: str = ""
    reason: str = ""
    trigger_data: Dict[str, Any] = field(default_factory=dict)

    _event_type_value: ClassVar[str] = "lifecycle_event"

    def validate(self) -> None:
        super().validate()
        _check_non_empty_str("card_id", self.card_id)
        _check_in_set("from_state", self.from_state, VALID_TRADE_CARD_STATES)
        _check_in_set("to_state", self.to_state, VALID_TRADE_CARD_STATES)
        if self.from_state == self.to_state:
            raise ValidationError(
                f"from_state and to_state must differ "
                f"(self-loop transition {self.from_state!r} not allowed)"
            )
        _check_non_empty_str("reason", self.reason)
        if not isinstance(self.trigger_data, dict):
            raise ValidationError("trigger_data must be dict")


@dataclass
class FillSimulation(Event):
    card_id: str = ""
    fill_attempt_type: str = ""
    fill_date: str = ""
    fill_decision: str = ""
    fill_price: Optional[float] = None
    ohlcv: Dict[str, Any] = field(default_factory=dict)
    fill_logic_applied: str = ""
    slippage_bps: int = 0
    data_source: str = ""
    data_source_sha256: str = ""

    _event_type_value: ClassVar[str] = "fill_simulation"

    def validate(self) -> None:
        super().validate()
        _check_non_empty_str("card_id", self.card_id)
        _check_in_set("fill_attempt_type", self.fill_attempt_type, VALID_FILL_ATTEMPT_TYPES)
        _check_iso_date("fill_date", self.fill_date)
        _check_in_set("fill_decision", self.fill_decision, VALID_FILL_DECISIONS)
        if not isinstance(self.ohlcv, dict):
            raise ValidationError("ohlcv must be dict")


# ============================================================
# Type registry for polymorphic deserialization
# ============================================================

_EVENT_TYPE_REGISTRY: Dict[str, Type[Event]] = {
    "scan_event": ScanEvent,
    "candidate_signal": CandidateSignal,
    "trade_card": TradeCard,
    "lifecycle_event": LifecycleEvent,
    "fill_simulation": FillSimulation,
}
