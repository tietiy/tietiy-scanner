"""
q_proposals_pending — query plugin returning pending/approved proposals
that target this signal's cohort.

Reads proposed_rules.json (output of rule_proposer.py). Filters to
proposals where target_signal or target_sector matches the input signal,
AND status is in {'pending', 'approved'}.

Bridge composer puts the result into evidence.active_proposals_relevant
on the SDR. Surfaces "we're proposing a rule change for this cohort"
to the user.

Mirrors evidence_collector._filter_relevant_proposals's match logic but
adds explicit status filter (excludes rejected / already_active).

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9.
"""

from typing import Optional


QUERY_NAME = "q_proposals_pending"
QUERY_DESCRIPTION = (
    "Returns pending/approved proposals targeting this signal's cohort"
)
INPUT_FILES = ["proposed_rules.json"]


_WILDCARD_VALUES = (None, "ANY", "")
_RELEVANT_STATUSES = {"pending", "approved"}


def run(signal: dict, proposals_data: dict) -> list:
    """Returns list of matching proposal dicts (each enriched with
    `source_file` and `matched_on`). Empty list if no matches."""
    if not isinstance(signal, dict) or not isinstance(proposals_data, dict):
        return []

    sig_type   = signal.get("signal_type") or signal.get("signal")
    sig_sector = signal.get("sector")

    proposals = proposals_data.get("proposals")
    if not isinstance(proposals, list) or not proposals:
        return []

    out: list = []
    for p in proposals:
        if not isinstance(p, dict):
            continue
        if p.get("status") not in _RELEVANT_STATUSES:
            continue

        target_signal = p.get("target_signal")
        target_sector = p.get("target_sector")

        signal_match = (
            target_signal not in _WILDCARD_VALUES
            and target_signal == sig_type
        )
        sector_match = (
            target_sector not in _WILDCARD_VALUES
            and target_sector == sig_sector
        )

        if not (signal_match or sector_match):
            continue

        if signal_match and sector_match:
            matched_on = "signal+sector"
        elif signal_match:
            matched_on = "signal"
        else:
            matched_on = "sector"

        enriched = dict(p)
        enriched["source_file"] = "proposed_rules.json"
        enriched["matched_on"] = matched_on
        out.append(enriched)

    return out
