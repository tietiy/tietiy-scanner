"""
Phase 5 — Live validation engine + tier classification.

For each Phase 4 survivor (combinations_lifetime.parquet):
  1. Run live_signal_matcher → live_n / live_w / live_l / live_wr
  2. Compute live_drift_vs_test = abs(live_wr − test_wr)
  3. Compute live_edge_pp = live_wr − cohort_baseline_wr
  4. Classify tier: VALIDATED / PRELIMINARY / WATCH / REJECTED

Tier rules (per Phase 5 spec):
  • Bull cohort (regime=Bull) → auto-WATCH (no live Bull data in current window)
  • REJECTED (live disagrees with backtest):
      live_n ≥ 5 AND (live_wr < baseline_wr OR live_wr < test_wr − 15pp)
  • VALIDATED (live confirms backtest with edge):
      live_n ≥ 10 AND live_wr ≥ test_wr − 5pp AND live_wr ≥ baseline + 5pp
  • PRELIMINARY (preliminary live confirmation, smaller sample):
      live_n ≥ 5 AND live_wr ≥ test_wr − 10pp AND live_wr ≥ baseline + 3pp
  • WATCH (insufficient live data; lifetime evidence preserved):
      live_n < 5
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

# ── Tier thresholds ───────────────────────────────────────────────────
N_VALIDATED = 10
N_PRELIMINARY = 5
N_REJECTED_FLOOR = 5  # need at least this many live signals to REJECT
VALIDATED_DRIFT_PP = 0.05      # live_wr ≥ test_wr − 5pp
VALIDATED_EDGE_PP = 0.05       # live_wr ≥ baseline + 5pp
PRELIMINARY_DRIFT_PP = 0.10    # live_wr ≥ test_wr − 10pp
PRELIMINARY_EDGE_PP = 0.03     # live_wr ≥ baseline + 3pp
REJECTED_DRIFT_PP = 0.15       # live_wr < test_wr − 15pp triggers REJECT
COHORT_BLOCK_REGIME = "Bull"   # all Bull combos → WATCH (no live Bull data)


@dataclass
class ValidationResult:
    """Per-combination tier verdict + supporting stats."""
    combo_id: str
    live_tier: str  # VALIDATED / PRELIMINARY / WATCH / REJECTED
    live_drift_vs_test: Optional[float]
    live_edge_pp: Optional[float]
    cohort_blocked: bool


def classify_tier(combo_row: dict,
                    match_result_dict: dict,
                    baseline_wr: Optional[float]) -> ValidationResult:
    """Apply tier classification logic per Phase 5 spec."""
    combo_id = combo_row["combo_id"]
    regime = combo_row["regime"]

    # Cohort blocking: Bull → auto-WATCH
    if regime == COHORT_BLOCK_REGIME:
        return ValidationResult(
            combo_id=combo_id, live_tier="WATCH",
            live_drift_vs_test=None, live_edge_pp=None,
            cohort_blocked=True,
        )

    live_n = match_result_dict.get("live_n", 0)
    live_wr = match_result_dict.get("live_wr")
    test_wr = combo_row.get("test_wr")

    # Insufficient live data → WATCH
    if live_n < N_PRELIMINARY or live_wr is None:
        return ValidationResult(
            combo_id=combo_id, live_tier="WATCH",
            live_drift_vs_test=None, live_edge_pp=None,
            cohort_blocked=False,
        )

    drift = abs(live_wr - test_wr) if test_wr is not None else None
    edge = (live_wr - baseline_wr) if baseline_wr is not None else None

    # REJECTED: live disagrees with backtest substantially
    if live_n >= N_REJECTED_FLOOR:
        rejected = False
        if baseline_wr is not None and live_wr < baseline_wr:
            rejected = True
        if (test_wr is not None
                and live_wr < test_wr - REJECTED_DRIFT_PP):
            rejected = True
        if rejected:
            return ValidationResult(
                combo_id=combo_id, live_tier="REJECTED",
                live_drift_vs_test=drift, live_edge_pp=edge,
                cohort_blocked=False,
            )

    # VALIDATED: strong live evidence
    if (live_n >= N_VALIDATED and test_wr is not None
            and live_wr >= test_wr - VALIDATED_DRIFT_PP
            and baseline_wr is not None
            and live_wr >= baseline_wr + VALIDATED_EDGE_PP):
        return ValidationResult(
            combo_id=combo_id, live_tier="VALIDATED",
            live_drift_vs_test=drift, live_edge_pp=edge,
            cohort_blocked=False,
        )

    # PRELIMINARY: smaller sample but supportive
    if (live_n >= N_PRELIMINARY and test_wr is not None
            and live_wr >= test_wr - PRELIMINARY_DRIFT_PP
            and baseline_wr is not None
            and live_wr >= baseline_wr + PRELIMINARY_EDGE_PP):
        return ValidationResult(
            combo_id=combo_id, live_tier="PRELIMINARY",
            live_drift_vs_test=drift, live_edge_pp=edge,
            cohort_blocked=False,
        )

    # Falls through filters → WATCH (live exists but neither validates nor rejects)
    return ValidationResult(
        combo_id=combo_id, live_tier="WATCH",
        live_drift_vs_test=drift, live_edge_pp=edge,
        cohort_blocked=False,
    )


def get_baseline_wr(baselines_data: dict, signal_type: str,
                      regime: str, horizon: str) -> Optional[float]:
    try:
        return baselines_data["cohorts"][signal_type][regime][horizon].get("wr")
    except KeyError:
        return None
