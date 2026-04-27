"""
watch_matcher — informational metadata layer. Matches signals against
active watch_patterns from data/mini_scanner_rules.json.

UNLIKE kill_matcher (Gate 1 → SKIP) and boost_matcher (Gate 3 → boost),
watch_matcher is NOT a gate. It does not influence bucket assignment,
filtering, or scoring. Matches surface as informational warnings via
SDR.evidence['watch_warnings'] (plural, list) and render in the L1
Telegram brief Caveats footer.

Multiple watch_patterns may match the same signal; all matches are
returned. Wildcard convention matches kill/boost (None or "ANY").

Pure function. Caller (premarket composer) loads watch_patterns from
truth_files["mini_scanner_rules"]["watch_patterns"] and passes the
list in. watch_matcher never touches files.

See doc/bridge_design_v1.md §1.1 (read-only by design),
output/eod_anomaly_2026-04-27.md (motivating analysis).
"""

from typing import Optional


_WILDCARD_VALUES = (None, "ANY")


def check_matches(signal: dict,
                  watch_patterns: list) -> list:
    """
    Returns list of all matching active watch_patterns, normalized
    for downstream consumption. Empty list if no match or malformed
    input. Plural-list-returning (unlike kill_matcher.check_match
    which returns first-match Optional[dict]) because multiple watch
    flags can apply to one signal and all should render.
    """
    if not isinstance(signal, dict):
        return []
    if not isinstance(watch_patterns, list) or not watch_patterns:
        return []

    sig_type   = signal.get("signal_type")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")

    if not sig_type:
        return []

    matches = []
    for pattern in watch_patterns:
        if not isinstance(pattern, dict):
            continue
        if pattern.get("active") is False:
            continue
        if not _matches(pattern, sig_type, sig_sector, sig_regime):
            continue
        matches.append(_normalize(pattern))
    return matches


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
    Returns a copy of pattern with extra flat aliases:
      watch_id    ← id
      descriptor  ← "<signal>" + " × <sector>" + " × <regime>"
                    built from non-wildcard dimensions only
                    (so a pattern with sector=null doesn't show "× None")
      matched_on  ← which dimensions were non-wildcard
    """
    out = dict(pattern)

    if "watch_id" not in out and "id" in pattern:
        out["watch_id"] = pattern["id"]

    parts = [pattern.get("signal") or "?"]
    if pattern.get("sector") not in _WILDCARD_VALUES:
        parts.append(pattern["sector"])
    if pattern.get("regime") not in _WILDCARD_VALUES:
        parts.append(pattern["regime"])
    out["descriptor"] = " × ".join(parts)

    matched = ["signal"]
    if pattern.get("sector") not in _WILDCARD_VALUES:
        matched.append("sector")
    if pattern.get("regime") not in _WILDCARD_VALUES:
        matched.append("regime")
    out["matched_on"] = "+".join(matched)

    return out
