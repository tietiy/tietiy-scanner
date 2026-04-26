"""
q_kill_match — query plugin wrapper around kill_matcher.check_match.

Sister to q_boost_match. Lets the query plugin registry expose kill
matching as a query, even though kill_matcher lives in
scanner.bridge.rules and is also called directly by evidence_collector.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §5 (Gate 1 — kill match).
"""

from typing import Optional


QUERY_NAME = "q_kill_match"
QUERY_DESCRIPTION = (
    "Wraps kill_matcher.check_match for the query plugin registry"
)
INPUT_FILES = ["mini_scanner_rules.json"]


def run(signal: dict,
        mini_scanner_rules: dict) -> Optional[dict]:
    """
    Returns the matched normalized kill_pattern dict, or None.
    Delegates fully to kill_matcher.check_match.
    """
    if not isinstance(signal, dict):
        return None
    if not isinstance(mini_scanner_rules, dict):
        return None

    from scanner.bridge.rules.kill_matcher import check_match

    kill_patterns = mini_scanner_rules.get("kill_patterns", [])
    return check_match(signal, kill_patterns)
