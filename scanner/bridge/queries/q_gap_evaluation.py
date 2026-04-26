"""
q_gap_evaluation — query plugin returning gap-vs-entry evaluation for
the L2 (POST_OPEN) phase.

Reads output/open_prices.json (written by open_validator at 09:32 IST),
matches the input signal by symbol + signal_date, classifies gap
severity, recomputes R:R using actual_open as effective entry, and
reports the R:R degradation vs the L1 trade_plan.

Used by:
- evidence_collector → fills evidence.gap_evaluation on POST_OPEN SDR
- bucket_engine (indirectly) → if entry_still_valid is False the
  composer forces bucket=SKIP regardless of Gate 1-4 outcome

For PRE_MARKET phase: open_prices.json doesn't exist yet, so this
query returns None — composer treats it as "not yet available," not
as a negative evaluation.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §3 (POST_OPEN day-flow), §12.2 (post-open
Telegram template), and scanner.open_validator for the upstream
open_prices.json schema + gap-status thresholds (3.0% SKIP, 1.5% WARN).
"""

from typing import Optional


QUERY_NAME = "q_gap_evaluation"
QUERY_DESCRIPTION = (
    "Gap-vs-entry evaluation: severity, entry_still_valid, "
    "R:R recomputed at actual_open"
)
INPUT_FILES = ["open_prices.json"]


_SEVERITY_MAP = {
    "OK":      "minor",
    "WARNING": "moderate",
    "SKIP":    "severe",
    "UNKNOWN": "unknown",
}
_VALID_GAP_STATUSES = {"OK", "WARNING"}


def run(signal: dict,
        open_prices: Optional[dict] = None) -> Optional[dict]:
    """Returns gap-evaluation dict for the signal, or None if no
    matching record exists in open_prices.json (pre-market phase,
    SA-derived signals not in today's batch, etc.)."""
    if not isinstance(signal, dict):
        return None
    if not isinstance(open_prices, dict):
        return None

    sig_symbol = signal.get("symbol")
    # Records use canonical 'date'; bridge-side may carry 'signal_date'
    sig_date = signal.get("date") or signal.get("signal_date")
    if not sig_symbol or not sig_date:
        return None

    record = _find_record(open_prices, sig_symbol, sig_date)
    if record is None:
        return None

    actual_open = record.get("actual_open")
    gap_pct = record.get("gap_pct")
    gap_status = record.get("gap_status") or "UNKNOWN"
    note = record.get("note") or ""

    gap_severity = _SEVERITY_MAP.get(gap_status, "unknown")
    entry_still_valid = gap_status in _VALID_GAP_STATUSES

    rr_at_actual_open = _recompute_rr(signal, actual_open)
    rr_degraded_pct = _rr_degradation(signal, rr_at_actual_open)

    return {
        "actual_open":        actual_open,
        "gap_pct":            gap_pct,
        "gap_status":         gap_status,
        "gap_severity":       gap_severity,
        "entry_still_valid":  entry_still_valid,
        "rr_at_actual_open":  rr_at_actual_open,
        "rr_degraded_pct":    rr_degraded_pct,
        "note":               note,
        "source_file":        "open_prices.json",
    }


def _find_record(open_prices: dict,
                 symbol: str,
                 signal_date: str) -> Optional[dict]:
    """Match by (symbol, signal_date). Both fields exist on
    open_prices records per open_validator._write_open_prices."""
    results = open_prices.get("results")
    if not isinstance(results, list):
        return None
    for r in results:
        if not isinstance(r, dict):
            continue
        if (r.get("symbol") == symbol
                and r.get("signal_date") == signal_date):
            return r
    return None


def _recompute_rr(signal: dict,
                  actual_open) -> Optional[float]:
    """R:R using actual_open as the effective entry.
    LONG:  reward = target - actual_open;  risk = actual_open - stop
    SHORT: reward = actual_open - target;  risk = stop - actual_open
    """
    if not isinstance(actual_open, (int, float)):
        return None

    stop = signal.get("stop")
    target = signal.get("target_price") or signal.get("target")
    direction = (signal.get("direction") or "LONG").upper()

    if not isinstance(stop, (int, float)):
        return None
    if not isinstance(target, (int, float)):
        return None

    try:
        if direction == "SHORT":
            risk = stop - actual_open
            reward = actual_open - target
        else:
            risk = actual_open - stop
            reward = target - actual_open
        if risk <= 0:
            return None
        return round(reward / risk, 2)
    except Exception:
        return None


def _rr_degradation(signal: dict,
                    rr_at_actual_open) -> Optional[float]:
    """Returns ((new_rr - original_rr) / original_rr) * 100.
    Negative = degraded (gap consumed expected upside).
    Positive = improved (favorable gap).
    """
    if not isinstance(rr_at_actual_open, (int, float)):
        return None

    original_rr = signal.get("rr") or signal.get("adjusted_rr")
    if not isinstance(original_rr, (int, float)) or original_rr == 0:
        return None

    return round(
        ((rr_at_actual_open - original_rr) / original_rr) * 100, 2)
