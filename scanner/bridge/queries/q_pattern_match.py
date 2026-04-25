"""
q_pattern_match — query plugin returning supporting + opposing patterns.

Reads patterns.json (output of pattern_miner.py), filters to those matching
the signal's signal_type + sector + regime, splits into supporting (positive
edge) and opposing (negative edge) groups.

Bridge composer puts results into evidence.patterns_supporting and
evidence.patterns_opposing on the SDR. PWA [why?] card renders both lists.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9 (background queries), §4 (SDR.evidence schema).
"""

from typing import Optional


QUERY_NAME = "q_pattern_match"
QUERY_DESCRIPTION = (
    "Returns supporting + opposing patterns from patterns.json"
)
INPUT_FILES = ["patterns.json"]


_WILDCARD_VALUES = (None, "ANY")
_TIER_ORDER = {"validated": 0, "preliminary": 1, "emerging": 2}


def run(signal: dict, patterns_data: dict) -> dict:
    """
    Returns {"supporting": [...], "opposing": [...]} of patterns
    that match the signal's signal_type + sector + regime, normalized
    to SDR.evidence schema (pattern_id, tier upper-case, wr as
    0-1 fraction, edge_vs_baseline_pp).
    """
    empty = {"supporting": [], "opposing": []}

    if not isinstance(signal, dict) or not isinstance(patterns_data, dict):
        return empty

    sig_type   = signal.get("signal_type")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")

    if not sig_type:
        return empty

    patterns = patterns_data.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        return empty

    supporting: list = []
    opposing:   list = []

    for p in patterns:
        if not isinstance(p, dict):
            continue
        if not _matches(p, sig_type, sig_sector, sig_regime):
            continue

        direction = p.get("direction")
        normalized = _normalize(p)

        if direction == "positive":
            supporting.append(normalized)
        elif direction == "negative":
            opposing.append(normalized)
        # neutral patterns excluded from both lists by design

    supporting.sort(key=_sort_key)
    opposing.sort(key=_sort_key)

    return {"supporting": supporting, "opposing": opposing}


def _matches(pattern: dict,
             sig_type: str,
             sig_sector: Optional[str],
             sig_regime: Optional[str]) -> bool:
    """
    A pattern matches a signal if every feature it specifies matches.
    A feature missing from pattern.features is treated as wildcard
    (so depth-1 patterns specifying only `signal` match any sector
    and any regime).
    """
    features = pattern.get("features")
    if not isinstance(features, dict):
        return False

    if not _feature_matches(features.get("signal"), sig_type,
                            required=True):
        return False
    if not _feature_matches(features.get("sector"), sig_sector):
        return False
    if not _feature_matches(features.get("regime"), sig_regime):
        return False
    return True


def _feature_matches(pattern_value, signal_value,
                     required: bool = False) -> bool:
    """
    pattern_value missing or wildcard → matches anything (unless
    required=True, in which case the pattern must specify a value).
    """
    if pattern_value in _WILDCARD_VALUES:
        return not required
    return pattern_value == signal_value


def _normalize(pattern: dict) -> dict:
    """
    Convert pattern_miner's schema into SDR.evidence shape.
    """
    wr_raw = pattern.get("wr")
    if isinstance(wr_raw, (int, float)):
        wr_fraction = round(wr_raw / 100.0, 4)
    else:
        wr_fraction = None

    tier_raw = pattern.get("tier")
    tier_upper = (tier_raw.upper()
                  if isinstance(tier_raw, str) else None)

    return {
        "pattern_id": pattern.get("id"),
        "tier": tier_upper,
        "n": pattern.get("n_resolved"),
        "wr": wr_fraction,
        "avg_pnl": pattern.get("avg_pnl"),
        "edge_vs_baseline_pp": pattern.get("edge_pct"),
        "source_file": "patterns.json",
    }


def _sort_key(p: dict):
    """Sort: validated > preliminary > emerging, then n descending."""
    tier = (p.get("tier") or "").lower()
    tier_rank = _TIER_ORDER.get(tier, 99)
    n = p.get("n") or 0
    return (tier_rank, -n)
