"""
q_gap_evaluation — Wave 3 stub.

Will be implemented when the L2 (post-open) composer is built. Reads
output/open_prices.json, compares the actual 9:15 open against
signal.entry, and returns gap-severity classification:
    {gap_pct, severity, entry_still_valid}

For Wave 2 (PRE_MARKET phase only): returns None unconditionally so
evidence_collector treats this evidence field as "not available"
rather than "evaluated negatively." Bridge composer should not block
on gap evaluation in pre-market (no opens exist yet).

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §3 (post-open phase), §4 (gap_caveat field).
"""

from typing import Optional


QUERY_NAME = "q_gap_evaluation"
QUERY_DESCRIPTION = (
    "[Wave 3 stub] Evaluates gap-up/gap-down severity vs entry trigger; "
    "not implemented in Wave 2"
)
INPUT_FILES = ["open_prices.json"]


def run(signal: dict,
        open_prices: Optional[dict] = None) -> Optional[dict]:
    """Wave 3 placeholder. Always returns None."""
    return None
