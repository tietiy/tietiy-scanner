"""
Phase 3 SUB-BLOCK 3B — Compute cohort baselines + emit baselines.json.

Runs BaselineComputer on the full enriched_signals.parquet across
9 cohorts (3 signal_types × 3 regimes) × 9 horizons = 81 cells.

For each cell: n, n_wins, n_losses, n_flat, wr, Wilson 95% interval,
binomial p-value vs 50%, return statistics.

Outputs lab/output/baselines.json + surfaces cross-INV validation cells:
  • UP_TRI × Bear × D6 vs D10 (INV-006 D10 candidate)
  • DOWN_TRI × all × D2 vs D6 (INV-013 D2 candidate)
  • All cohorts × D1 (BTST overnight bias context per INV-012)

Run:
    .venv/bin/python lab/analyses/inv_phase3_compute_baselines.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from baseline_computer import (  # noqa: E402
    BaselineComputer, DEFAULT_HORIZONS, DEFAULT_CACHE_DIR,
)

INPUT_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _LAB_ROOT / "output" / "baselines.json"


def main():
    print("─" * 72)
    print("Phase 3 SUB-BLOCK 3B — Compute cohort baselines")
    print("─" * 72)

    t0 = time.time()
    print(f"\nLoading: {INPUT_PATH}")
    df = pd.read_parquet(INPUT_PATH)
    n_rows = len(df)
    print(f"  signals: {n_rows}")
    print(f"  cohorts: {df['signal'].value_counts().to_dict()}")
    print(f"  regimes: {df['regime'].value_counts().to_dict()}")

    bc = BaselineComputer(df, cache_dir=DEFAULT_CACHE_DIR,
                            entry_col="entry_price")

    print(f"\nComputing outcomes across horizons {DEFAULT_HORIZONS}...")
    print(f"  ~{n_rows * len(DEFAULT_HORIZONS)} signal-horizon outcomes; "
          f"progress every 10K signals.")
    t_compute0 = time.time()
    outcomes = bc.compute_outcomes(horizons=DEFAULT_HORIZONS)
    compute_time = time.time() - t_compute0
    print(f"  Outcome compute complete: {compute_time:.1f}s "
          f"({len(outcomes)} rows)")
    # Quick sanity on outcome distribution
    print(f"  Outcome label distribution: "
          f"{outcomes['label'].value_counts().to_dict()}")

    print("\nAggregating per cohort × horizon...")
    aggregated = BaselineComputer.aggregate(outcomes)

    out_payload = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "input_dataset": str(INPUT_PATH.relative_to(_LAB_ROOT.parent)),
        "n_signals_total": n_rows,
        "horizons_computed": list(DEFAULT_HORIZONS),
        "cohorts": aggregated["cohorts"],
        "validation": aggregated["validation"],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as fh:
        json.dump(out_payload, fh, indent=2, default=str)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    total_time = time.time() - t0
    print(f"Total Phase 3B runtime: {total_time / 60:.1f} min "
          f"({total_time:.0f}s)")

    # Validation summary
    print()
    print("═" * 72)
    print("VALIDATION SUMMARY")
    print("═" * 72)
    v = aggregated["validation"]
    print(f"Total cells: {v['cells_total']}")
    print(f"  high confidence (n≥100): {v['cells_high_confidence']}")
    print(f"  low confidence (30≤n<100): {v['cells_low_confidence']}")
    print(f"  too low (n<30): {v['cells_too_low']}")
    print(f"  skipped insufficient (n_wl<10): "
          f"{v['cells_skipped_insufficient_n']}")

    # Cross-INV validation surface
    print()
    print("═" * 72)
    print("CROSS-INV VALIDATION CELLS")
    print("═" * 72)
    coh = aggregated["cohorts"]

    def _show(sig_type, regime, horizon_key, note=""):
        try:
            cell = coh[sig_type][regime][horizon_key]
        except KeyError:
            print(f"  {sig_type} × {regime} × {horizon_key}: MISSING")
            return
        if cell.get("wr") is None:
            print(f"  {sig_type} × {regime} × {horizon_key}: "
                  f"too few signals (n={cell.get('n', 0)})")
            return
        wl_lower = cell["wilson_lower_95"]
        wl_upper = cell["wilson_upper_95"]
        print(f"  {sig_type:<12} × {regime:<8} × {horizon_key:<3}  "
              f"n={cell['n']:>5}  W={cell['n_wins']:>4}  L={cell['n_losses']:>4}  "
              f"WR={cell['wr']:.1%}  [{wl_lower:.1%}, {wl_upper:.1%}]  "
              f"avg_ret={cell['avg_return_pct'] * 100 if cell['avg_return_pct'] else 0:.2f}%  "
              f"{note}")

    print("\n— INV-006 (UP_TRI D6 vs D10 across regimes) —")
    for regime in ("Bear", "Bull", "Choppy"):
        _show("UP_TRI", regime, "D6")
        _show("UP_TRI", regime, "D10", "← INV-006 candidate")

    print("\n— INV-013 (DOWN_TRI D2 vs D6 across regimes) —")
    for regime in ("Bear", "Bull", "Choppy"):
        _show("DOWN_TRI", regime, "D2", "← INV-013 candidate")
        _show("DOWN_TRI", regime, "D6")

    print("\n— INV-012 BTST context (D1 across all cohorts) —")
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        for regime in ("Bear", "Bull", "Choppy"):
            _show(sig, regime, "D1")

    print("\n— BULL_PROXY × D6 (sanity) —")
    for regime in ("Bear", "Bull", "Choppy"):
        _show("BULL_PROXY", regime, "D6")


if __name__ == "__main__":
    main()
