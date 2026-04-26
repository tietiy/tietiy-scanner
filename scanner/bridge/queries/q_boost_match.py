"""
q_boost_match — query plugin wrapper around boost_matcher.check_match.

Lets the query plugin registry expose boost matching as a query, even
though boost_matcher lives in scanner.bridge.rules and is also called
directly by evidence_collector. The wrapper is here for symmetry with
the rest of the queries/ folder and forward-flexibility (e.g., if
future composers want to dispatch boost matching via the registry
rather than direct import).

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §5 (Gate 3 — boost match).
"""

from typing import Optional


QUERY_NAME = "q_boost_match"
QUERY_DESCRIPTION = (
    "Wraps boost_matcher.check_match for the query plugin registry"
)
INPUT_FILES = ["mini_scanner_rules.json"]


def run(signal: dict,
        mini_scanner_rules: dict) -> Optional[dict]:
    """
    Returns the matched normalized boost_pattern dict, or None.
    Delegates fully to boost_matcher.check_match.
    """
    if not isinstance(signal, dict):
        return None
    if not isinstance(mini_scanner_rules, dict):
        return None

    # Imported inside run() to avoid any chance of circular import at
    # module load time (registry imports queries/, queries import rules/,
    # rules don't depend on queries — this keeps the order one-way).
    from scanner.bridge.rules.boost_matcher import check_match

    boost_patterns = mini_scanner_rules.get("boost_patterns", [])
    return check_match(signal, boost_patterns)
