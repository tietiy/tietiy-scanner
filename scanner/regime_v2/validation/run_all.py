"""Run all validations sequentially and produce summary."""
from __future__ import annotations

import os
import sys

from scanner.regime_v2.validation import (
    v1_cohort_preservation,
    v2_visual_sanity,
    v3_transition_reasonableness,
    v5_cohort_predictive_power,
)


def main():
    out_dir = "output/regime_v2/validation"
    os.makedirs(out_dir, exist_ok=True)

    print("\n" + "=" * 80)
    print("VALIDATION 1 — Cohort Preservation")
    print("=" * 80)
    r1 = v1_cohort_preservation.run()

    print("\n" + "=" * 80)
    print("VALIDATION 2 — Visual Sanity Check (chart generation)")
    print("=" * 80)
    r2 = v2_visual_sanity.run()

    print("\n" + "=" * 80)
    print("VALIDATION 3 — Transition Reasonableness")
    print("=" * 80)
    r3 = v3_transition_reasonableness.run()

    print("\n" + "=" * 80)
    print("VALIDATION 5 — Cohort-Wise Predictive Power")
    print("=" * 80)
    r5 = v5_cohort_predictive_power.run()

    # Summary
    summary = {
        "V1": r1.get("OVERALL"),
        "V2": "READY_FOR_REVIEW",
        "V3": r3.get("OVERALL"),
        "V5": r5.get("OVERALL"),
    }
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for v, status in summary.items():
        emoji = "✅" if status == "PASS" else ("📊" if status == "READY_FOR_REVIEW" else "❌")
        print(f"  {emoji} {v}: {status}")

    # Write master summary
    md_path = "doc/regime_v2_design/validation_results.md"
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w") as f:
        f.write("# Regime v2 — Validation Results\n\n")
        f.write(f"**Generated:** 2026-05-13\n\n")
        f.write("**Mode:** VIX-degraded (no India VIX file in repo; design §04 fallback enforced)\n\n")
        f.write("## Summary\n\n")
        f.write("| Validation | Outcome | Detail |\n|---|---|---|\n")
        for v, status in summary.items():
            emoji = "✅" if status == "PASS" else ("📊" if status == "READY_FOR_REVIEW" else "❌")
            f.write(f"| {v} | {emoji} {status} | see `output/regime_v2/validation/{v.lower()}_*.md` |\n")
        f.write("\n## Visual sanity charts\n\n")
        for chart in r2.get("charts", []):
            f.write(f"- `doc/regime_v2_design/{chart}`\n")
        f.write("\n## Detailed reports\n\n")
        f.write("- [V1 — Cohort Preservation](../output/regime_v2/validation/v1_cohort_preservation.md)\n")
        f.write("- [V3 — Transition Reasonableness](../output/regime_v2/validation/v3_transition_reasonableness.md)\n")
        f.write("- [V5 — Cohort Predictive Power](../output/regime_v2/validation/v5_cohort_predictive_power.md)\n")
    print(f"\nMaster summary written to {md_path}")

    # Decision per design §V6
    gating = ["V1", "V3", "V5"]
    fails = [v for v in gating if summary.get(v) != "PASS"]
    if fails:
        print(f"\n❌ GATING VALIDATIONS FAILED: {fails}")
        print("   Per design §V6: this triggers hard rollback (R1/R2/R5) or soft retune (R6/R7/R8).")
        print("   Phase 5 (promotion) BLOCKED.")
        return 1
    print("\n✅ All gating validations PASS. Ready for Phase 4 (side-by-side shadow run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
