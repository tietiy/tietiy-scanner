"""
SDR — Signal Decision Record.

The atomic unit of the bridge. Every signal becomes one SDR per phase.
SDRs are immutable per phase — L2 produces new POST_OPEN SDRs, never mutates L1.

See doc/bridge_design_v1.md §4 for full schema and field rationale.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Optional

from scanner.bridge.rules.thresholds import SDR_SCHEMA_VERSION


_VALID_BUCKETS = {"TAKE_FULL", "TAKE_SMALL", "WATCH", "SKIP"}
_VALID_PHASES = {"PRE_MARKET", "POST_OPEN", "EOD"}
_VALID_DIRECTIONS = {"LONG", "SHORT"}

_REQUIRED_NONEMPTY_STR_FIELDS = (
    "sdr_id",
    "signal_id",
    "phase_timestamp",
    "market_date",
    "symbol",
    "signal_type",
    "sector",
    "regime",
    "bucket_reason_short",
    "bucket_reason_long",
)


def _empty_counter_evidence() -> dict:
    return {
        "patterns_against": [],
        "data_quality_flags": [],
        "regime_concerns": [],
        "cluster_warnings": [],
    }


def _empty_learner_hooks() -> dict:
    return {
        "self_query_candidates": [],
        "confidence_band": "medium",
        "uncertainty_dimensions": [],
        "gap_flags": [],
    }


@dataclass
class SDR:
    SCHEMA_VERSION: ClassVar[int] = SDR_SCHEMA_VERSION

    sdr_id: str
    signal_id: str
    phase: str
    phase_timestamp: str
    market_date: str

    symbol: str
    signal_type: str
    direction: str
    sector: str
    regime: str
    age_days: int

    trade_plan: dict
    bucket: str
    bucket_reason_short: str
    bucket_reason_long: str
    gap_caveat: dict
    evidence: dict
    display: dict
    audit: dict

    is_sa_variant: bool = False
    origin: Optional[str] = None
    bucket_changed: bool = False
    previous_bucket: Optional[str] = None
    bucket_change_reason: Optional[str] = None

    counter_evidence: dict = field(
        default_factory=_empty_counter_evidence)
    learner_hooks: dict = field(
        default_factory=_empty_learner_hooks)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SDR":
        return cls(**data)

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.bucket not in _VALID_BUCKETS:
            return False, (
                f"invalid bucket: {self.bucket!r} "
                f"(expected one of {sorted(_VALID_BUCKETS)})")
        if self.phase not in _VALID_PHASES:
            return False, (
                f"invalid phase: {self.phase!r} "
                f"(expected one of {sorted(_VALID_PHASES)})")
        if self.direction not in _VALID_DIRECTIONS:
            return False, (
                f"invalid direction: {self.direction!r} "
                f"(expected one of {sorted(_VALID_DIRECTIONS)})")
        for fname in _REQUIRED_NONEMPTY_STR_FIELDS:
            v = getattr(self, fname)
            if not isinstance(v, str) or not v:
                return False, (
                    f"required string field empty or "
                    f"non-string: {fname}")
        return True, None
