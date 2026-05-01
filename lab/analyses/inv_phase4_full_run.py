"""
Phase 4 SUB-BLOCK 4F — Full run across all active cohort cells.

Pipeline:
  1. Generate combinations for all active (signal × regime × horizon) cells
     (per cohort_horizon_config; 20 cells × ~27K combos each = 541K combos)
  2. Pre-compute outcomes once per signal × horizon (D1, D2, D3, D5, D6, D8,
     D10, D15, D20)
  3. Walk-forward test all combinations (train 2011-18 / val 2019-22 /
     test 2023-25)
  4. Apply iteration-2 filter pipeline (FDR + drift ≤12pp + ≤1 calendar)
  5. Save:
       lab/output/combinations_tested.parquet (pre-filter, for re-iteration)
       lab/output/combinations_lifetime.parquet (filtered survivors)

HALT (per task spec):
  • Runtime > 4 hours
  • Total survivors > 20,000
  • Bear cohort has 0 survivors across all horizons
  • Triangle_quality_ascending appears as Tier S in Bear cohort (contradicts
    Phase 2 KILL finding)
  • Any single cohort represents >70% of survivors

Run:
    .venv/bin/python lab/analyses/inv_phase4_full_run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402
from combination_generator import generate_combinations  # noqa: E402
from walk_forward_tester import (  # noqa: E402
    run_walk_forward, precompute_outcomes,
)
from cohort_horizon_config import (  # noqa: E402
    list_active_cohort_cells, COHORT_HORIZONS, COHORT_SKIP,
)
from inv_phase4_filter import apply_filters, print_funnel  # noqa: E402

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
BASELINES_PATH = _LAB_ROOT / "output" / "baselines.json"
COMBOS_PATH = _LAB_ROOT / "output" / "combinations_pending.parquet"
CACHE_DIR = _LAB_ROOT / "cache"
TESTED_OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_tested.parquet"
SURVIVORS_OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_lifetime.parquet"

MAX_RUNTIME_SEC = 4 * 60 * 60  # 4-hour HALT
MAX_SURVIVORS = 20_000  # HALT if exceeded
MAX_COHORT_SHARE = 0.70  # HALT if any single cohort > 70% of survivors


def _check_halt_conditions(survivors: pd.DataFrame) -> list[str]:
    """Return list of triggered HALT messages (empty if all green)."""
    halts = []
    n = len(survivors)
    if n > MAX_SURVIVORS:
        halts.append(f"survivors={n} > {MAX_SURVIVORS} cap")
    # Bear cohort 0-survivors check
    bear = survivors[survivors["regime"] == "Bear"]
    if len(bear) == 0:
        halts.append("Bear cohort: 0 survivors across all horizons")
    # Cohort imbalance
    if n > 0:
        per_cohort = survivors.groupby(
            ["signal_type", "regime", "horizon"]).size()
        max_share = per_cohort.max() / n
        if max_share > MAX_COHORT_SHARE:
            largest = per_cohort.idxmax()
            halts.append(
                f"cohort imbalance: {largest} = {max_share:.0%} > "
                f"{MAX_COHORT_SHARE:.0%}")
    return halts


def _check_triangle_kill_contradiction(survivors: pd.DataFrame,
                                            combos: pd.DataFrame) -> bool:
    """Verify triangle_quality_ascending=high is NOT Tier S in Bear cohort."""
    if len(survivors) == 0:
        return False
    bear_s = survivors[(survivors["regime"] == "Bear")
                          & (survivors["tier"] == "S")]
    if len(bear_s) == 0:
        return False
    # Merge with combos to get feature_*_id
    feat_cols = ["feature_a_id", "feature_b_id",
                  "feature_c_id", "feature_d_id"]
    merged = bear_s.merge(combos[["combo_id"] + feat_cols],
                              on="combo_id", how="left")

    def _has_tri_high(row):
        for slot in ("a", "b", "c", "d"):
            fid = row.get(f"feature_{slot}_id")
            lvl = row.get(f"feature_{slot}_level")
            if fid == "triangle_quality_ascending" and lvl == "high":
                return True
        return False

    contradicting = merged.apply(_has_tri_high, axis=1)
    return bool(contradicting.any())


def main():
    print("─" * 72)
    print("Phase 4 SUB-BLOCK 4F — Full run on all active cohort cells")
    print("─" * 72)

    t_total = time.time()

    # ── Inputs ────────────────────────────────────────────────────────
    print(f"\nLoading: {ENRICHED_PATH}")
    signals = pd.read_parquet(ENRICHED_PATH)
    signals["scan_date"] = pd.to_datetime(signals["scan_date"])
    print(f"  signals: {len(signals)}")

    print(f"Loading: {IMPORTANCE_PATH}")
    with open(IMPORTANCE_PATH) as fh:
        importance = json.load(fh)
    print(f"Loading: {BASELINES_PATH}")
    with open(BASELINES_PATH) as fh:
        baselines = json.load(fh)

    registry = FeatureRegistry.load_all()
    active_cells = list_active_cohort_cells()
    print(f"\nActive cohort cells: {len(active_cells)}")

    # ── Generate combinations (or load if already generated) ──────────
    if COMBOS_PATH.exists():
        print(f"\nLoading existing combinations: {COMBOS_PATH}")
        combos = pd.read_parquet(COMBOS_PATH)
        print(f"  {len(combos)} combinations loaded")
    else:
        print(f"\nGenerating combinations for {len(active_cells)} cells...")
        combos = generate_combinations(signals, importance, registry,
                                          active_cells, verbose=False)
        print(f"  {len(combos)} combinations generated")
        combos.to_parquet(COMBOS_PATH, index=False)

    # ── Pre-compute outcomes ──────────────────────────────────────────
    needed_horizons = sorted({int(h[1:]) for _, _, h in active_cells})
    print(f"\nPre-computing outcomes for horizons {needed_horizons}...")
    t0 = time.time()
    outcomes_by_h = precompute_outcomes(signals, needed_horizons, CACHE_DIR)
    print(f"  Outcome compute: {time.time() - t0:.1f}s "
          f"(across {sum(len(v) for v in outcomes_by_h.values())} signal-horizon rows)")

    # ── Runtime check before walk-forward ────────────────────────────
    elapsed = time.time() - t_total
    if elapsed > MAX_RUNTIME_SEC:
        sys.exit(f"HALT: runtime {elapsed/60:.1f}min already exceeds "
                 f"{MAX_RUNTIME_SEC/60:.0f}min before walk-forward")

    # ── Walk-forward test all combinations ───────────────────────────
    print(f"\nWalk-forward testing {len(combos)} combinations...")
    print(f"  Progress checkpoints: 25% / 50% / 75% via every-10K reporting.")
    t0 = time.time()
    tested = run_walk_forward(combos, signals, outcomes_by_h, baselines,
                                  registry, progress_every=20_000)
    wf_time = time.time() - t0
    print(f"  Walk-forward: {wf_time/60:.1f} min "
          f"({wf_time*1000/len(combos):.1f} ms/combo)")

    # Save pre-filter walk-forward output
    TESTED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tested.to_parquet(TESTED_OUTPUT_PATH, index=False)
    size_mb = TESTED_OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"  Saved {TESTED_OUTPUT_PATH} ({size_mb:.1f} MB)")

    # Runtime check
    elapsed = time.time() - t_total
    if elapsed > MAX_RUNTIME_SEC:
        sys.exit(f"HALT: runtime {elapsed/60:.1f}min > "
                 f"{MAX_RUNTIME_SEC/60:.0f}min")

    # ── Apply iteration-2 filter pipeline ─────────────────────────────
    print(f"\nApplying iteration-2 filter pipeline...")
    survivors, funnel = apply_filters(tested, len(tested),
                                          combos_definitions=combos)
    print_funnel(funnel)

    # ── HALT condition checks ────────────────────────────────────────
    halts = _check_halt_conditions(survivors)
    triangle_contradict = _check_triangle_kill_contradiction(survivors, combos)
    if triangle_contradict:
        halts.append("triangle_quality_ascending=high is Tier S in Bear cohort "
                     "(contradicts Phase 2 KILL finding)")
    if halts:
        print()
        print("⚠ HALT conditions triggered:")
        for h in halts:
            print(f"  • {h}")
        sys.exit(1)

    # ── Per-cohort distribution ──────────────────────────────────────
    print()
    print("═" * 72)
    print("PER-COHORT × HORIZON SURVIVOR DISTRIBUTION")
    print("═" * 72)
    print(f"{'cohort':<32} {'tested':>9} {'survivors':>9} {'S':>5} {'A':>5} {'B':>5}")
    for (s, r, h) in active_cells:
        cell_tested = len(tested[(tested["signal_type"] == s)
                                     & (tested["regime"] == r)
                                     & (tested["horizon"] == h)])
        cell_surv = survivors[(survivors["signal_type"] == s)
                                  & (survivors["regime"] == r)
                                  & (survivors["horizon"] == h)]
        s_n = (cell_surv["tier"] == "S").sum()
        a_n = (cell_surv["tier"] == "A").sum()
        b_n = (cell_surv["tier"] == "B").sum()
        print(f"  {s + ' × ' + r + ' × ' + h:<30} "
              f"{cell_tested:>9} {len(cell_surv):>9} "
              f"{s_n:>5} {a_n:>5} {b_n:>5}")

    # ── Save survivors ───────────────────────────────────────────────
    SURVIVORS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    survivors.to_parquet(SURVIVORS_OUTPUT_PATH, index=False)
    size_kb = SURVIVORS_OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {SURVIVORS_OUTPUT_PATH} "
          f"({len(survivors)} survivors, {size_kb:.1f} KB)")

    total_runtime = time.time() - t_total
    print()
    print("═" * 72)
    print("FINAL SUMMARY")
    print("═" * 72)
    print(f"Total runtime: {total_runtime/60:.1f} min")
    print(f"Combinations tested: {len(tested)}")
    print(f"Survivors: {len(survivors)} "
          f"({len(survivors)/len(tested)*100:.2f}%)")
    print(f"  Tier S: {funnel['tier_S']}")
    print(f"  Tier A: {funnel['tier_A']}")
    print(f"  Tier B: {funnel['tier_B']}")
    print(f"\n4F complete — awaiting findings doc commit.")


if __name__ == "__main__":
    main()
