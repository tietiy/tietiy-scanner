"""
q_exact_cohort — query plugin returning aggregate stats for the signal's
exact cohort (signal_type × sector × regime × age) from resolved records.

Reads from signal_history.json records using canonical field names
(`signal`, `sector`, `regime`, `age`, `result`, `pnl_pct`, `mfe_pct`,
`mae_pct`). Accepts either bridge naming (`signal_type` / `age_days`)
or canonical naming on the input signal arg.

Bridge composer puts the result into evidence.exact_cohort on the SDR.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §4 (SDR.evidence schema).
"""

from typing import Optional


QUERY_NAME = "q_exact_cohort"
QUERY_DESCRIPTION = (
    "Aggregate stats for the signal's exact cohort "
    "(signal × sector × regime × age) from resolved records"
)
INPUT_FILES = ["signal_history.json"]


# Canonical outcome-based resolution (matches pattern_miner.py).
# A record's `result` field cannot distinguish DAY6_WIN from DAY6_LOSS
# (both labelled `EXITED`); we MUST use `outcome` for win/loss math.
_TERMINAL_OUTCOMES = {
    "TARGET_HIT", "STOP_HIT",
    "DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT",
}
_WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}

# tier classifications (per spec)
_TIER_VALIDATED_N  = 15
_TIER_VALIDATED_WR = 0.85
_TIER_PRELIM_N     = 8
_TIER_PRELIM_WR    = 0.75


def run(signal: dict, history_data: dict) -> Optional[dict]:
    if not isinstance(signal, dict) or not isinstance(history_data, dict):
        return None

    sig_type   = _sig_type(signal)
    sig_sector = signal.get("sector")
    sig_regime = signal.get("regime")
    sig_age    = _sig_age(signal)

    if not sig_type or not sig_sector or not sig_regime:
        return None
    if sig_age is None:
        return None

    history = history_data.get("history")
    if not isinstance(history, list):
        return None

    matches = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("outcome") not in _TERMINAL_OUTCOMES:
            continue
        if r.get("signal") != sig_type:
            continue
        if r.get("sector") != sig_sector:
            continue
        if r.get("regime") != sig_regime:
            continue
        if r.get("age") != sig_age:
            continue
        matches.append(r)

    n = len(matches)
    if n == 0:
        return None

    wins = sum(1 for r in matches if r.get("outcome") in _WIN_OUTCOMES)
    wr = wins / n

    avg_pnl = _mean_field(matches, "pnl_pct")
    avg_mfe = _mean_field(matches, "mfe_pct")
    avg_mae = _mean_field(matches, "mae_pct")

    return {
        "n": n,
        "wr": round(wr, 4),
        "avg_pnl": avg_pnl,
        "avg_mfe": avg_mfe,
        "avg_mae": avg_mae,
        "tier_status": _classify_tier(n, wr),
    }


def _sig_type(signal: dict) -> Optional[str]:
    """Bridge naming preferred; fall back to canonical."""
    v = signal.get("signal_type")
    if v is None:
        v = signal.get("signal")
    return v


def _sig_age(signal: dict) -> Optional[int]:
    """Bridge naming preferred; fall back to canonical. age=0 is valid."""
    v = signal.get("age_days")
    if v is None:
        v = signal.get("age")
    if isinstance(v, (int, float)):
        return int(v)
    return None


def _mean_field(records: list, field: str) -> Optional[float]:
    values = [r.get(field) for r in records
              if isinstance(r.get(field), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _classify_tier(n: int, wr: float) -> str:
    if n >= _TIER_VALIDATED_N and wr >= _TIER_VALIDATED_WR:
        return "validated"
    if n >= _TIER_PRELIM_N and wr >= _TIER_PRELIM_WR:
        return "preliminary"
    return "emerging"
