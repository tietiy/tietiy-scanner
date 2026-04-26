"""
_history_reader — read L1 SDRs from the dated bridge_state_history file.

L2 (POST_OPEN) composer needs to know what L1 (PRE_MARKET) decided so it
can populate `previous_bucket` and `bucket_change_reason` on POST_OPEN
SDRs whose bucket flipped.

state_writer.write_state writes a verbatim dated copy of bridge_state.json
to `output/bridge_state_history/{market_date}_{phase}.json`. This module
reads that file and returns L1's SDRs keyed by signal_id for fast lookup.

Why a separate file (not part of state_writer): state_writer is the
single write chokepoint and only writes. Reads from history live closer
to the consumer (composers/), and stay one-way to keep the dependency
DAG clean (composers → state_writer, never the reverse).

See doc/bridge_design_v1.md §1.7 (immutable phase records),
§3 (POST_OPEN day-flow needs previous_bucket).
"""

import json
import logging
import os
from typing import Optional


_HISTORY_DIRNAME = "bridge_state_history"
_logger = logging.getLogger(__name__)


def read_l1_sdrs(market_date: str,
                 output_dir: str = "output") -> dict:
    """Return L1 history record for the given market_date.

    Always returns a dict with the same keys, even on miss/error:

    Args:
        market_date: YYYY-MM-DD
        output_dir: typically "output"

    Returns:
        {
            "found": bool,                    # True iff file existed AND parsed
            "sdrs_by_signal_id": dict,        # {signal_id: sdr_dict, ...}
            "phase_status": Optional[str],    # "OK"/"DEGRADED"/"ERROR"/"SKIPPED"
            "compose_timestamp": Optional[str],   # state.phase_timestamp
            "raw_state": Optional[dict],      # the full bridge_state contents
        }
    """
    miss = _empty_result()

    if not isinstance(market_date, str) or not market_date:
        return miss

    path = os.path.join(
        output_dir, _HISTORY_DIRNAME, f"{market_date}_PRE_MARKET.json")

    if not os.path.exists(path):
        return miss

    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        _logger.warning(
            "[_history_reader] L1 history file %s malformed: %s",
            path, e)
        return miss
    except OSError as e:
        _logger.warning(
            "[_history_reader] L1 history file %s unreadable: %s",
            path, e)
        return miss

    if not isinstance(state, dict):
        _logger.warning(
            "[_history_reader] L1 history file %s root is not an object",
            path)
        return miss

    sdrs_by_id = _index_signals(state.get("signals"))

    return {
        "found":              True,
        "sdrs_by_signal_id":  sdrs_by_id,
        "phase_status":       state.get("phase_status"),
        "compose_timestamp":  state.get("phase_timestamp"),
        "raw_state":          state,
    }


def _empty_result() -> dict:
    return {
        "found":              False,
        "sdrs_by_signal_id":  {},
        "phase_status":       None,
        "compose_timestamp":  None,
        "raw_state":          None,
    }


def _index_signals(signals) -> dict:
    """Build {signal_id: sdr_dict}. Skip entries lacking signal_id."""
    out: dict = {}
    if not isinstance(signals, list):
        return out
    for s in signals:
        if not isinstance(s, dict):
            continue
        sid = s.get("signal_id")
        if not isinstance(sid, str) or not sid:
            continue
        out[sid] = s
    return out
