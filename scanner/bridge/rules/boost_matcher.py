"""
boost_matcher — Gate 3 of bucket assignment. Matches signal against active boost_patterns.

Boost patterns come from data/mini_scanner_rules.json. Tier A → TAKE_FULL.
Tier B → TAKE_SMALL. No match → falls through to Gate 4 (evidence consensus).

The matcher handles wildcard sector/regime (null in the live schema, "ANY"
defensively) and respects the per-pattern `active` flag. Tier A is scanned
before Tier B, so a signal matching both ends up TAKE_FULL.

Pure function. Caller (bucket_engine / evidence_collector) loads boost_patterns
from mini_scanner_rules.json and passes the list in. boost_matcher never
touches files.

Returned dict is the original boost_pattern with normalized aliases added
so downstream consumers can read flat keys (boost_id, n, wr, avg_pnl,
promotion_date, matched_on) regardless of the on-disk schema's nesting.

See doc/bridge_design_v1.md §5.1 (Gate 3), §6.1-6.2 (TAKE_FULL/TAKE_SMALL).
"""

from typing import Optional


_WILDCARD_VALUES = (None, "ANY")
_TIER_PRIORITY = ("A", "B")


def check_match(signal: dict,
                boost_patterns: list) -> Optional[dict]:
    """
    Returns the highest-priority matching boost_pattern (Tier A before
    Tier B), normalized for downstream consumption. None if no match.
    """
    if not isinstance(signal, dict):
        return None
    if not isinstance(boost_patterns, list) or not boost_patterns:
        return None

    sig_type   = signal.get("signal_type")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")

    if not sig_type:
        return None

    for target_tier in _TIER_PRIORITY:
        for pattern in boost_patterns:
            if not isinstance(pattern, dict):
                continue
            if pattern.get("active") is False:
                continue
            if pattern.get("tier") != target_tier:
                continue
            if not _matches(pattern, sig_type, sig_sector, sig_regime):
                continue
            return _normalize(pattern)

    return None


def _matches(pattern: dict,
             sig_type: str,
             sig_sector: Optional[str],
             sig_regime: Optional[str]) -> bool:
    if pattern.get("signal") != sig_type:
        return False

    p_sector = pattern.get("sector")
    if p_sector not in _WILDCARD_VALUES and p_sector != sig_sector:
        return False

    p_regime = pattern.get("regime")
    if p_regime not in _WILDCARD_VALUES and p_regime != sig_regime:
        return False

    return True


def _normalize(pattern: dict) -> dict:
    """
    Returns a copy of pattern with extra flat aliases so downstream
    code (bucket_engine, SDR.evidence) can read consistent keys.
    """
    out = dict(pattern)

    # boost_id ← id
    if "boost_id" not in out and "id" in pattern:
        out["boost_id"] = pattern["id"]

    # Lift evidence.{n, wr, avg_pnl} to top level if not already there
    ev = pattern.get("evidence") or {}
    if isinstance(ev, dict):
        for key in ("n", "wr", "avg_pnl"):
            if key not in out and key in ev:
                out[key] = ev[key]

    # promotion_date ← added_date
    if "promotion_date" not in out and "added_date" in pattern:
        out["promotion_date"] = pattern["added_date"]

    # matched_on shows which dimensions were non-wildcard in the rule
    matched = ["signal"]
    if pattern.get("sector") not in _WILDCARD_VALUES:
        matched.append("sector")
    if pattern.get("regime") not in _WILDCARD_VALUES:
        matched.append("regime")
    out["matched_on"] = "+".join(matched)

    return out
