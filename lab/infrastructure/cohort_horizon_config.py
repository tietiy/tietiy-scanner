"""
Phase 4 cohort horizon configuration — derived from Phase 3 baseline findings.

Per-cohort horizon defaults: which D-N hold horizons to test for each
(signal_type × regime) cohort, based on Phase 3 baseline analysis showing
where each cohort's WR peaks and where extension helps/hurts.

Skip list: cells where Phase 3 baseline drops below ~40% (DOWN_TRI Bear far
horizons, BULL_PROXY Choppy far horizons) — combinations would need impossible
edge to be useful.

Reference: lab/analyses/PHASE-03_baselines.md "Implications for Phase 4".
"""
from __future__ import annotations

# Per-cohort horizons — Phase 3 said:
# - UP_TRI Bear/Bull baseline climbs through D20; default D6/D10/D15
# - UP_TRI Choppy baseline peaks D5/D6 then decays; D10 hurts
# - DOWN_TRI all baselines decay rapidly; D1/D2 only
# - BULL_PROXY all peak D3/D5 then decay
COHORT_HORIZONS: dict[tuple[str, str], list[str]] = {
    ("UP_TRI", "Bear"):     ["D6", "D10", "D15"],
    ("UP_TRI", "Bull"):     ["D6", "D10", "D15"],
    ("UP_TRI", "Choppy"):   ["D5", "D6"],
    ("DOWN_TRI", "Bear"):   ["D1", "D2"],
    ("DOWN_TRI", "Bull"):   ["D1", "D2"],
    ("DOWN_TRI", "Choppy"): ["D1", "D2"],
    ("BULL_PROXY", "Bear"):   ["D3", "D5"],
    ("BULL_PROXY", "Bull"):   ["D3", "D5"],
    ("BULL_PROXY", "Choppy"): ["D3", "D5"],
}

# Cells to skip entirely — baselines too far below 50% for combinations to help
COHORT_SKIP: list[tuple[str, str, str]] = [
    ("DOWN_TRI", "Bear", "D15"),
    ("DOWN_TRI", "Bear", "D20"),
    ("BULL_PROXY", "Choppy", "D15"),
    ("BULL_PROXY", "Choppy", "D20"),
]


def list_active_cohort_cells() -> list[tuple[str, str, str]]:
    """Return [(signal_type, regime, horizon), ...] for all active cells
    (after applying COHORT_HORIZONS expansions and COHORT_SKIP exclusions)."""
    skip_set = set(COHORT_SKIP)
    cells = []
    for (sig, reg), horizons in COHORT_HORIZONS.items():
        for h in horizons:
            if (sig, reg, h) not in skip_set:
                cells.append((sig, reg, h))
    return cells


def cohort_key(signal_type: str, regime: str, horizon: str) -> str:
    """Canonical string key for cohort cell."""
    return f"{signal_type}|{regime}|{horizon}"


if __name__ == "__main__":
    cells = list_active_cohort_cells()
    print(f"Active cohort cells: {len(cells)}")
    for c in cells:
        print(f"  {c[0]:<12} × {c[1]:<8} × {c[2]}")
    print(f"\nSkipped cells: {len(COHORT_SKIP)}")
    for c in COHORT_SKIP:
        print(f"  {c[0]} × {c[1]} × {c[2]}")
