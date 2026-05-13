# 09 — Auto Analyst

## Status: DOCUMENTED BUT NEVER BUILT

`scanner/auto_analyst.py` is referenced in canonical docs:
- `doc/session_context.md` line 272: "`scanner/auto_analyst.py` — nightly if ≥5 new resolutions"
- `doc/bridge_design_v1.md` line 208: "23:00   auto_analyst.py runs (existing, conditional on 5+ resolutions)"
- `doc/bridge_design_v1.md` line 1445: "| colab_insights.json | auto_analyst.py | READ |"
- `doc/bridge_design_v1.md` line 1488: "| 23:00 | auto_analyst (conditional) |"

But the file does not exist on any branch:
```
$ git log --all --oneline -- scanner/auto_analyst.py
(no output)
```

No commit on `main`, `shadow_ops_v1`, `backtest-lab`, `rule_031_audit`, `vp-leakage-fix`, or `v2-integration` has ever touched the path `scanner/auto_analyst.py`.

## What was supposed to happen

Per `bridge_design_v1.md`, auto_analyst was the **conditional nightly LLM analyst** that would consume `colab_insights.json` (a separate analysis output from Colab notebooks) and produce a summary if ≥5 new resolutions occurred that day. It would feed into the bridge composer as additional context.

This role has been effectively absorbed by **`scanner/brain/brain_reason.py`** (Wave 5 Step 5), which runs nightly via `brain.yml` at 22:00 IST and produces evidence-grounded LLM reasoning across cohort_promotion, regime_shift, and exposure_correlation gates. The auto_analyst design was made redundant by the brain layer.

## What actually exists for analyst-style analysis

| Path | Role | Status |
|---|---|---|
| `scripts/analyze_full.py` | Full-history analysis script that wrote `output/analysis_report_2026-04-27.md` | ✅ One-shot manual analysis (not scheduled) |
| `scanner/brain/brain_reason.py` | LLM gates: cohort_promotion / regime_shift / exposure_correlation | ✅ Shipped, gated on production-fire |
| `scanner/weekly_intelligence.py` | Weekly aggregator → `output/weekly_intelligence_latest.json` | ✅ Shipped, runs Sun 20:00 IST |

## Cross-reference with brain proposals

The brain has already absorbed everything auto_analyst was supposed to do:
- "≥5 new resolutions" trigger → brain runs daily regardless; cohort_health.json computes Wilson-bounded tiers across the resolved population.
- "LLM analyst" → 3 LLM gates per brain run, $0.10/run.
- "colab_insights.json" → never wired; brain consumes truth files directly.

## Verdict

**Auto-analyst is a phantom dependency.** Any doc reference to it can be updated to point at the brain layer. No code to build, no work to do — except clean up the design doc references for clarity.

## What I could not determine

- Whether `colab_insights.json` was ever produced and where it would live if so. Not found in `output/`. Possibly an artifact from a Colab notebook the user runs outside the scanner repo (memory mentions "lucifer trigger → Colab backtest context").
