"""
q_anti_pattern — query plugin returning the strongest opposing pattern.

Reads patterns.json (output of pattern_miner.py), finds opposing patterns
(direction == 'negative') matching the signal's identity, and returns
the SINGLE STRONGEST opposing match. Strongest = highest tier, then
largest n, then most-negative edge_pct.

Distinguished from q_pattern_match: that query returns supporting +
opposing as a dict for general evidence display. This query returns
ONLY the strongest single opposing match for alert/warn generation.

Bridge composer puts the result into evidence.anti_pattern_check on
the SDR. Used by bucket_engine to decide whether to downgrade Gate-4
classifications.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §4 (SDR.evidence.anti_pattern_check).
"""

from typing import Optional


QUERY_NAME = "q_anti_pattern"
QUERY_DESCRIPTION = (
    "Returns strongest opposing pattern (negative direction) matching "
    "signal — used for alert/warn generation"
)
INPUT_FILES = ["patterns.json"]


_WILDCARD_VALUES = (None, "ANY")
_TIER_RANK = {"validated": 0, "preliminary": 1, "emerging": 2}


def run(signal: dict, patterns_data: dict) -> Optional[dict]:
    """Returns the strongest opposing pattern dict normalized to
    SDR.evidence shape, or None."""
    if not isinstance(signal, dict) or not isinstance(patterns_data, dict):
        return None

    sig_type   = signal.get("signal_type")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")
    if not sig_type:
        return None

    patterns = patterns_data.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        return None

    matches = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        if p.get("direction") != "negative":
            continue
        if not _matches(p, sig_type, sig_sector, sig_regime):
            continue
        matches.append(p)

    if not matches:
        return None

    # Sort: tier rank ASC (validated first), then n_resolved DESC,
    # then edge_pct ASC (most negative first).
    matches.sort(key=lambda p: (
        _TIER_RANK.get((p.get("tier") or "").lower(), 99),
        -(p.get("n_resolved") or 0),
        (p.get("edge_pct") or 0),
    ))

    return _normalize(matches[0])


def _matches(pattern: dict,
             sig_type: str,
             sig_sector: Optional[str],
             sig_regime: Optional[str]) -> bool:
    features = pattern.get("features")
    if not isinstance(features, dict):
        return False
    # signal must be present and exact
    p_sig = features.get("signal")
    if p_sig in _WILDCARD_VALUES or p_sig != sig_type:
        return False
    # sector/regime: missing = wildcard
    p_sec = features.get("sector")
    if p_sec not in _WILDCARD_VALUES and p_sec != sig_sector:
        return False
    p_reg = features.get("regime")
    if p_reg not in _WILDCARD_VALUES and p_reg != sig_regime:
        return False
    return True


def _normalize(pattern: dict) -> dict:
    """Convert pattern_miner schema → SDR.evidence shape."""
    wr_raw = pattern.get("wr")
    wr = round(wr_raw / 100.0, 4) if isinstance(wr_raw, (int, float)) else None
    tier_raw = pattern.get("tier")
    tier = tier_raw.upper() if isinstance(tier_raw, str) else None
    return {
        "pattern_id": pattern.get("id"),
        "tier": tier,
        "n": pattern.get("n_resolved"),
        "wr": wr,
        "avg_pnl": pattern.get("avg_pnl"),
        "edge_vs_baseline_pp": pattern.get("edge_pct"),
        "source_file": "patterns.json",
    }
