"""
q_outcome_today — Wave 3 stub.

Will be implemented for the L4 (EOD) composer. Looks up the signal in
signal_history and returns today's terminal outcome (one of TARGET_HIT,
STOP_HIT, DAY6_WIN, DAY6_LOSS, DAY6_FLAT) plus pnl_pct, mfe_pct,
mae_pct.

For Wave 2 (PRE_MARKET phase only): returns None unconditionally — no
outcomes have happened yet at compose time. Bridge composer should not
block on outcome lookup in pre-market.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §3 (EOD phase), §4 (outcome fields).
"""

from typing import Optional


QUERY_NAME = "q_outcome_today"
QUERY_DESCRIPTION = (
    "[Wave 3 stub] Returns today's resolution outcome for a signal; "
    "not implemented in Wave 2"
)
INPUT_FILES = ["signal_history.json"]


def run(signal: dict,
        history_data: Optional[dict] = None) -> Optional[dict]:
    """Wave 3 placeholder. Always returns None."""
    return None
