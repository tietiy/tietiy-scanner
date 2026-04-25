"""
validity_checker — Gate 2 of bucket assignment.

Validates basic trade-plan sanity before a signal can be considered for any
non-SKIP bucket. Pure function — stateless, no I/O, no dependencies beyond
thresholds.

Failure here means SKIP regardless of how strong the cohort or boost match
might look. R:R below 1.5 means the math doesn't work, period.

See doc/bridge_design_v1.md §5.1 (Gate 2).
"""

from typing import Optional

from scanner.bridge.rules.thresholds import (
    VALIDITY_MAX_AGE_DAYS_DEFAULT,
    VALIDITY_MAX_AGE_DOWN_TRI,
    VALIDITY_MIN_RR,
)


_REQUIRED_FIELDS = ("signal_type", "sector", "regime", "rr")


def check(signal: dict) -> tuple[bool, Optional[str]]:
    """
    Returns (is_valid, reason). First failure wins; reason is None
    when valid. See module docstring for ordering rationale.
    """
    if not isinstance(signal, dict):
        return False, "signal is not a dict"

    # Step 1 — explicit entry_valid=False from mini_scanner
    if signal.get("entry_valid") is False:
        reason = signal.get("entry_invalid_reason") or "no reason given"
        return False, f"Entry flagged invalid by mini_scanner: {reason}"

    # Step 2 — R:R floor (only when rr is numeric; missing rr is
    # caught by step 4)
    rr = signal.get("rr")
    if isinstance(rr, (int, float)) and rr < VALIDITY_MIN_RR:
        return False, f"R:R {rr} below minimum {VALIDITY_MIN_RR}"

    # Step 3 — age bounds (only when age_days is numeric)
    sigtype = signal.get("signal_type")
    age = signal.get("age_days")
    if isinstance(age, (int, float)):
        if sigtype == "DOWN_TRI":
            if age > VALIDITY_MAX_AGE_DOWN_TRI:
                return False, (
                    f"DOWN_TRI age {age} > "
                    f"{VALIDITY_MAX_AGE_DOWN_TRI} — edge gone "
                    f"after age {VALIDITY_MAX_AGE_DOWN_TRI} per backtest"
                )
        else:
            if age > VALIDITY_MAX_AGE_DAYS_DEFAULT:
                return False, (
                    f"Age {age} > "
                    f"{VALIDITY_MAX_AGE_DAYS_DEFAULT}, signal stale"
                )

    # Step 4 — missing required fields (defensive)
    for field in _REQUIRED_FIELDS:
        if signal.get(field) is None:
            return False, f"Missing required field: {field}"

    return True, None
