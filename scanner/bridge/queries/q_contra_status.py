"""
q_contra_status — query plugin returning contra-shadow tracking status
for kill rules blocking this signal.

Reads contra_shadow.json (output of contra_tracker.py). Filters shadows
to those whose origin matches the input signal (origin_signal_type +
sector + regime). If at least one matching shadow exists, aggregates
stats and returns a single status dict.

Bridge composer puts the result into evidence display when a kill rule
is blocking — lets the user see "rule blocked, contra at 8/30 with 75%
inverted-LONG WR."

Schema per `contra_tracker._record_shadow` and the live contra_shadow.json:
  - top-level: {schema_version, total_tracked, resolved_count,
                pending_count, shadows[]}
  - shadow: {id, kill_rule_id, origin_signal_type, sector, regime,
             outcome (None | CONTRA_WIN | CONTRA_LOSS | CONTRA_FLAT),
             pnl_pct, ...}

Win definition: outcome == "CONTRA_WIN" (per outcome_evaluator.py:952).

State thresholds:
  INSUFFICIENT     — n_resolved < 5
  TRACKING         — 5 <= n_resolved < 30
  READY_FOR_REVIEW — n_resolved >= 30 (matches contra_tracker.unlock_threshold)

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §7 (contra-tracker integration).
"""

from typing import Optional


QUERY_NAME = "q_contra_status"
QUERY_DESCRIPTION = (
    "Returns contra-shadow status for kill rules blocking this signal"
)
INPUT_FILES = ["contra_shadow.json"]


_CONTRA_WIN = "CONTRA_WIN"
_RESOLVED_OUTCOMES = {"CONTRA_WIN", "CONTRA_LOSS", "CONTRA_FLAT"}

_INSUFFICIENT_MAX_N = 5      # below this → INSUFFICIENT
_REVIEW_THRESHOLD = 30       # at/above → READY_FOR_REVIEW
_WILDCARD_VALUES = (None, "ANY", "")


def run(signal: dict,
        contra_data: dict) -> Optional[dict]:
    """Returns aggregated status dict if any matching shadow exists,
    else None."""
    if not isinstance(signal, dict) or not isinstance(contra_data, dict):
        return None

    sig_type   = signal.get("signal_type") or signal.get("signal")
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")
    if not sig_type:
        return None

    shadows = contra_data.get("shadows")
    if not isinstance(shadows, list) or not shadows:
        return None

    matching = []
    for s in shadows:
        if not isinstance(s, dict):
            continue
        if s.get("origin_signal_type") != sig_type:
            continue
        # sector / regime: if shadow specifies non-wildcard, must match
        s_sec = s.get("sector")
        if s_sec not in _WILDCARD_VALUES and sig_sector is not None \
                and s_sec != sig_sector:
            continue
        s_reg = s.get("regime")
        if s_reg not in _WILDCARD_VALUES and sig_regime is not None \
                and s_reg != sig_regime:
            continue
        matching.append(s)

    if not matching:
        return None

    # Aggregate. Take kill_rule_id from the first matching shadow
    # (they should all share the same kill rule per design — kill_001
    # blocks DOWN_TRI×Bank, all those shadows have kill_rule_id=kill_001).
    kill_id = matching[0].get("kill_rule_id")

    resolved = [s for s in matching
                if s.get("outcome") in _RESOLVED_OUTCOMES]
    n_resolved = len(resolved)

    if n_resolved == 0:
        shadow_wr = None
        shadow_avg_pnl = None
    else:
        wins = sum(1 for s in resolved
                   if s.get("outcome") == _CONTRA_WIN)
        shadow_wr = round(wins / n_resolved, 4)
        pnls = [s.get("pnl_pct") for s in resolved
                if isinstance(s.get("pnl_pct"), (int, float))]
        shadow_avg_pnl = round(sum(pnls) / len(pnls), 2) if pnls else None

    state, next_milestone = _classify_state(n_resolved)

    last_updated = _latest_update(matching)

    return {
        "kill_id": kill_id,
        "shadow_n": n_resolved,
        "shadow_wr": shadow_wr,
        "shadow_avg_pnl": shadow_avg_pnl,
        "state": state,
        "last_updated": last_updated,
        "next_milestone": next_milestone,
    }


def _classify_state(n_resolved: int):
    if n_resolved >= _REVIEW_THRESHOLD:
        return "READY_FOR_REVIEW", None
    if n_resolved < _INSUFFICIENT_MAX_N:
        return "INSUFFICIENT", f"n={_INSUFFICIENT_MAX_N} minimum sample"
    return "TRACKING", f"n={_REVIEW_THRESHOLD} review trigger"


def _latest_update(shadows: list) -> Optional[str]:
    """Most recent recorded_at / resolved_at timestamp across shadows."""
    candidates = []
    for s in shadows:
        for field in ("resolved_at", "recorded_at"):
            v = s.get(field)
            if isinstance(v, str) and v:
                candidates.append(v)
    return max(candidates) if candidates else None
