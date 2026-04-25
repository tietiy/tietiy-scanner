"""
kill_matcher — Gate 1 of bucket assignment. Matches signal against active kill_patterns.

Kill patterns come from data/mini_scanner_rules.json. Match → SKIP (Gate 1 fires
first, blocks regardless of other factors). The matcher handles wildcard sector
and regime (null in live schema, "ANY" defensively), respects per-pattern
`active` flag, and normalizes returned dict for bucket_engine consumption.

Pure function. Caller (bucket_engine) loads kill_patterns from
mini_scanner_rules.json and passes the list in. kill_matcher never touches files.

Gate 1 fires before Gate 2 (validity), Gate 3 (boost), Gate 4 (evidence). A kill
match is the strongest possible "do not trade" signal — short-circuits all
further analysis.

See doc/bridge_design_v1.md §5.1 (Gate 1), §6.4 (SKIP example via kill).
"""

from typing import Optional


_WILDCARD_VALUES = (None, "ANY")


def check_match(signal: dict,
                kill_patterns: list) -> Optional[dict]:
    """
    Returns the first matching active kill_pattern, normalized for
    downstream consumption. None if no match.
    """
    if not isinstance(signal, dict):
        return None
    if not isinstance(kill_patterns, list) or not kill_patterns:
        return None

    sig_type   = signal.get("signal_type")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")

    if not sig_type:
        return None

    for pattern in kill_patterns:
        if not isinstance(pattern, dict):
            continue
        if pattern.get("active") is False:
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
    code (bucket_engine, SDR.evidence) can read consistent keys
    regardless of the on-disk schema's nesting.
    """
    out = dict(pattern)

    # kill_id ← id
    if "kill_id" not in out and "id" in pattern:
        out["kill_id"] = pattern["id"]

    # Lift evidence.{n, wr, avg_pnl} to top level if not already there
    ev = pattern.get("evidence") or {}
    if isinstance(ev, dict):
        for key in ("n", "wr", "avg_pnl"):
            if key not in out and key in ev:
                out[key] = ev[key]

    # active_since ← added_date
    if "active_since" not in out and "added_date" in pattern:
        out["active_since"] = pattern["added_date"]

    # active_shadow ← contra_shadow_tracked
    if ("active_shadow" not in out
            and "contra_shadow_tracked" in pattern):
        out["active_shadow"] = pattern["contra_shadow_tracked"]

    # matched_on shows which dimensions were non-wildcard in the rule
    matched = ["signal"]
    if pattern.get("sector") not in _WILDCARD_VALUES:
        matched.append("sector")
    if pattern.get("regime") not in _WILDCARD_VALUES:
        matched.append("regime")
    out["matched_on"] = "+".join(matched)

    return out
