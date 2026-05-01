# COMBINATION ENGINE MASTER PLAN
**TIE TIY Lab — Phase 1 through Phase 6**

**Authored:** 2026-05-XX
**Owner:** Abhishek (decisions) + Claude (execution partner)
**Status:** APPROVED — execute phase by phase
**Branch:** backtest-lab
**Stored at:** lab/COMBINATION_ENGINE_PLAN.md

---

## Purpose

Build a 6-phase Lab pipeline that:
1. Extracts ~110 features per signal from existing Lab data
2. Reduces to top 20 features via live winner analysis
3. Computes universe baselines per cohort
4. Generates and tests feature combinations across 15-year backtest
5. Validates surviving combinations against 1-month live database
6. Compiles final high-conviction barcodes.json

End state: barcodes.json — ranked list of validated trading rules ready for production analyser consumption.

---

## Discipline — applies to all phases

1. Each phase = its own CC session. Phases never mixed in single session.
2. NO main branch modifications. All work on backtest-lab branch.
3. NO mini_scanner_rules.json edits. Production integration deferred.
4. NO scanner/ modifications. Lab work only.
5. Schema-first. Lock data structures before writing code.
6. Validation gate at end of each phase. Never proceed if validation fails.
7. Surface diff before commit. User approves block-by-block.
8. Atomic commits per logical unit within a phase.
9. Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
10. git pull --rebase × 3 retry per push.
11. Each phase produces persistent artifacts (parquet/JSON) at known paths.
12. If unexpected error: HALT, commit WIP, push, end session.
13. NO promotion decisions during these phases.
14. NO production deployment work.

---

## Inputs (already in repo)

- lab/output/backtest_signals_with_regime.parquet (105,987 signals, 15-year)
- lab/cache/*.parquet (188 stock OHLCV + 9 indices)
- data/signal_history.json (118 live resolved signals + open)
- lab/output/regime_history.parquet
- lab/output/sector_momentum_history.parquet
- lab/infrastructure/hypothesis_tester.py (41/41 tests passing)
- All prior INV findings (INV-001/002/003/006/007/010/012/013)

---

## Outputs (to be produced by pipeline)

- After Phase 1: lab/output/enriched_signals.parquet
- After Phase 2: lab/output/feature_importance.json
- After Phase 3: lab/output/baselines.json
- After Phase 4: lab/output/combinations_lifetime.parquet
- After Phase 5: lab/output/combinations_live_validated.parquet
- After Phase 6: lab/output/barcodes.json + lab/output/barcode_clusters.parquet

Plus per-phase findings.md documenting what was computed, validation results, surface findings for user review.

---

## PHASE 1 — Feature extraction

**Goal:** Compute ~110 features per signal. One-time enrichment pass.

**Duration:** ~1-2 weeks (feature definition iteration + build + validation)

**Structure:**

A. Feature library design (separate session before code)
- Lock down ~110 feature definitions
- Group into 6 families: compression / institutional_zone / momentum / volume / regime / pattern
- Each feature has: feature_id, family, value_type, range, level_thresholds, direction, mechanism, data_source
- Stored as lab/feature_library/<feature_id>.json (plugin pattern)
- User reviews + approves each family's feature set

B. Feature library implementation
- lab/feature_library/ folder created
- One JSON file per feature definition
- lab/infrastructure/feature_loader.py reads all definitions, returns feature registry

C. Feature extractor module
- lab/infrastructure/feature_extractor.py
- Reads backtest_signals_with_regime.parquet
- For each signal row, computes all 110 features by reading from cache + applying feature_library functions
- Writes enriched_signals.parquet with feat_<feature_id> columns

D. Validation gate
- Schema check: all 110 feature columns present
- NaN check: <5% NaN per feature (otherwise diagnose)
- Sample-row review: 10 random rows surfaced; user spot-checks values
- Distribution check: each feature's distribution sane (no all-zeros, no all-same-value)

E. Findings doc
- lab/analyses/PHASE-01_feature_extraction.md
- Documents feature library structure, computation method per family, validation results

**Output:**
- lab/output/enriched_signals.parquet
- lab/feature_library/<feature_id>.json × 110
- lab/infrastructure/feature_loader.py
- lab/infrastructure/feature_extractor.py
- lab/analyses/PHASE-01_feature_extraction.md

**Commit pattern:**
- Atomic commit per family of features (6 commits)
- Atomic commit for feature_loader + feature_extractor
- Atomic commit for enriched_signals.parquet generation
- Atomic commit for findings doc

---

## PHASE 2 — Feature importance via live winner analysis

**Goal:** Rank 110 features by their predictive power on live signal outcomes. Reduce to top 20 for combination search.

**Duration:** ~3-5 days

**Structure:**

A. Live signal feature enrichment
- For each of 118 resolved live signals in signal_history.json: find matching scan_date + symbol in enriched_signals, extract feature vector, join with live outcome (W/L/F)
- lab/infrastructure/live_feature_joiner.py
- OUTPUT: lab/output/live_signals_with_features.parquet

B. Feature importance analysis
- lab/analyses/inv_phase2_importance.py
- For each of 110 features:
  - Univariate WR comparison: WR(feature_high) vs WR(feature_low)
  - Mutual information with outcome
  - Statistical test (t-test or Mann-Whitney)
- Multivariate: random forest classifier on outcome, feature importance
- Multivariate: logistic regression coefficients
- Combine three rankings via rank aggregation (Borda count)

C. Output
- lab/output/feature_importance.json
- Ranked list of 110 features with importance scores from each method
- Top 20 flagged as PRIORITY for Phase 4
- Bottom 90 retained for potential Phase 4 expansion if needed

D. Validation gate
- Top 20 features include both known-good (volume signature, regime) and potentially-novel features
- User reviews top 20 for domain plausibility
- User can override (force-include or force-exclude features)

E. Findings doc
- lab/analyses/PHASE-02_feature_importance.md
- Documents methodology, top 20 with scores, bottom 20 explanations, surprises

**Output:**
- lab/output/live_signals_with_features.parquet
- lab/output/feature_importance.json
- lab/analyses/PHASE-02_feature_importance.md
- lab/infrastructure/live_feature_joiner.py
- lab/analyses/inv_phase2_importance.py

---

## PHASE 3 — Cohort baseline computation

**Goal:** Compute universe baseline WR per (signal × regime × hold_horizon). Corrects for INV-012 finding that 50% null is wrong.

**Duration:** ~3 days

**Structure:**

A. Baseline computer
- lab/infrastructure/baseline_computer.py
- For each combination of:
  - signal_type ∈ {UP_TRI, DOWN_TRI, BULL_PROXY, GAP_BREAKOUT, BTST_*}
  - regime ∈ {Bear, Bull, Choppy}
  - hold_horizon ∈ {D1, D2, D3, D6, D10}
- Compute unconditional WR across full universe × full history at that cohort + horizon
- Wilson lower bound, p-value vs 50%, n

B. Output structure
- lab/output/baselines.json
- Schema: baselines[signal_type][regime][hold_horizon] = {n, wr, wilson_lower, p_value}

C. Validation gate
- BTST baseline ~67% (matches INV-012 finding)
- Swing baseline ~50-55%
- Per-regime baselines reasonable
- User spot-checks 5 entries

D. Findings doc
- lab/analyses/PHASE-03_baselines.md
- Documents methodology, baseline table, comparison to prior INV-012 finding

**Output:**
- lab/output/baselines.json
- lab/infrastructure/baseline_computer.py
- lab/analyses/PHASE-03_baselines.md

---

## PHASE 4 — Combination engine

**Goal:** Test feature combinations on top 20 features × cohorts. Filter by lifetime backtest evidence.

**Duration:** ~2 weeks

**Structure:**

A. Combination generator
- lab/infrastructure/combination_generator.py
- Generates all (k-feature, cohort) combinations where:
  - k ∈ {1, 2, 3, 4} — search up to 4-feature combos
  - features ∈ top 20 from Phase 2
  - each feature × 3 levels (low/med/high)
- Combined with cohort space:
  - signal_type × sector × regime
- Estimated output: ~20K-200K combinations

B. Walk-forward tester
- lab/infrastructure/walk_forward_tester.py
- Train: 2011-2018
- Validate: 2019-2022
- Test: 2023-2025
- For each combination:
  - compute_n, compute_wr per period
  - drift = train_wr - test_wr
  - wilson lower bound
  - p-value vs cohort baseline (from Phase 3)

C. Filter pipeline
- lab/analyses/inv_phase4_combination_engine.py
- Apply filters in order:
  - n ≥ 30 in train AND validate AND test
  - test_wr ≥ baseline_wr + 5pp
  - drift |train_wr - test_wr| ≤ 15pp
  - wilson_lower_95 ≥ 0.55 (or signal-appropriate)
  - p_value < 0.01 (after Bonferroni or FDR correction)
- Surviving combinations → combinations_lifetime.parquet

D. Output
- lab/output/combinations_lifetime.parquet
- Each row = one tested combination with full stats:
  - combo_id, signal_type, sector, regime, feature_combo (sorted list of feature_id+level), feature_count
  - train_n, train_wr, validate_n, validate_wr, test_n, test_wr, drift_pp
  - wilson_lower_95, p_value, baseline_wr, edge_pp, tier

E. Validation gate
- Survivor count: 50-2000 expected
- Top 20 surviving combinations spot-checked by user
- Each surviving combination has reasonable mechanism (not random curve-fit)

F. Findings doc
- lab/analyses/PHASE-04_combination_engine.md
- Documents methodology, survivor distribution, top survivors, concerns

**Output:**
- lab/output/combinations_lifetime.parquet
- lab/infrastructure/combination_generator.py
- lab/infrastructure/walk_forward_tester.py
- lab/analyses/inv_phase4_combination_engine.py
- lab/analyses/PHASE-04_combination_engine.md

---

## PHASE 5 — Live validation

**Goal:** Validate Phase 4 survivors against 1-month live database. Reject combinations that don't generalize to recent live conditions.

**Duration:** ~3-5 days

**Structure:**

A. Live validator
- lab/infrastructure/live_validator.py
- For each combination in combinations_lifetime.parquet:
  - find matching live signals (cohort match + feature levels match)
  - compute live_n, live_wr
- Filter: keep combinations where:
  - live_n ≥ 5 (statistical floor)
  - live_wr within 10pp of test_wr (from Phase 4 test period)

B. Tier classification
- VALIDATED: live_n ≥ 10 AND live_wr ≥ test_wr - 5pp
- PRELIMINARY: live_n 5-9 AND live_wr ≥ test_wr - 10pp
- WATCH: live_n < 5 (insufficient live data; revisit in 1-3 months)
- REJECTED: live_wr < test_wr - 10pp (combination doesn't generalize)

C. Output
- lab/output/combinations_live_validated.parquet
- Each row = combination with live_n, live_wr, tier, comparison to lifetime stats

D. Validation gate
- At least 1 VALIDATED combination per regime preferred
- Reasonable rejection rate (50-80% expected)
- User reviews top 10 VALIDATED combinations

E. Findings doc
- lab/analyses/PHASE-05_live_validation.md
- Documents methodology, tier distribution, top survivors, rejected analysis

**Output:**
- lab/output/combinations_live_validated.parquet
- lab/infrastructure/live_validator.py
- lab/analyses/PHASE-05_live_validation.md

---

## PHASE 6 — Barcode compilation

**Goal:** Convert validated combinations into final barcodes.json with deduplication, mechanism explanations, ranking.

**Duration:** ~3-5 days

**Structure:**

A. Barcode clusterer
- lab/infrastructure/barcode_clusterer.py
- Identifies near-identical combinations (e.g., overlapping feature sets in same cohort)
- Clusters via Jaccard similarity on feature sets
- Within each cluster, keeps strongest representative

B. Mechanism gate
- User-mediated session: each cluster's representative reviewed
- User provides mechanism explanation in plain English
- Barcodes without mechanism explanation marked INACTIVE
- Optional: LLM-suggested mechanisms surfaced for user review/edit

C. Final compilation
- lab/infrastructure/barcode_compiler.py
- Reads validated combinations + cluster representatives + mechanisms
- Outputs barcodes.json per schema:

```json
{
  "schema_version": 1,
  "generated_at": "...",
  "barcodes": [
    {
      "barcode_id": "BC_001",
      "signal_type": "UP_TRI",
      "cohort": {"sector": "Auto", "regime": "Bear"},
      "features_required": [
        {"feature_id": "vol_ratio_20d", "level": "high"},
        {"feature_id": "ema50_distance", "level": "low"}
      ],
      "evidence": {
        "lifetime_n": 87, "lifetime_wr": 0.91,
        "live_n": 12, "live_wr": 0.92,
        "baseline_wr": 0.50, "edge_pp": 0.41,
        "wilson_lower": 0.78, "tier": "S"
      },
      "mechanism": "Auto sector outperforms in Bear via defensive rotation; high volume + close-to-EMA50 = institutional accumulation entry",
      "verdict": "TAKE_FULL",
      "active": true,
      "created_date": "2026-05-XX"
    }
  ]
}
```

- Sorts by tier (S/A/B/PRELIMINARY/WATCH) then by edge_pp magnitude

D. Output
- lab/output/barcodes.json (final)
- lab/output/barcode_clusters.parquet (clustering audit trail)

E. Validation gate
- barcodes.json count: 20-100 expected
- Each barcode has all required fields populated
- Mechanism field non-empty for all ACTIVE barcodes
- User final-review pass

F. Findings doc
- lab/analyses/PHASE-06_barcode_compilation.md
- Documents clustering methodology, mechanism review process, final barcode summary

**Output:**
- lab/output/barcodes.json
- lab/output/barcode_clusters.parquet
- lab/infrastructure/barcode_clusterer.py
- lab/infrastructure/barcode_compiler.py
- lab/analyses/PHASE-06_barcode_compilation.md

---

## Inter-phase protocol

Between each phase:
1. CC ends current phase session, commits + pushes all work.
2. User reviews findings doc.
3. User approves moving to next phase OR requests refinement.
4. If refinement requested: prior phase reopened in new CC session.
5. If approved: next phase begins in fresh CC session.

NEVER: Two phases in same session.
NEVER: Skip validation gate.
NEVER: Production integration during these 6 phases.

---

## Where this leaves us at end

After Phase 6 complete:
- barcodes.json contains 20-100 high-conviction trading rules
- Each rule has: cohort, feature requirements, evidence, mechanism, tier
- Production integration becomes well-defined separate workstream:
  - scanner reads barcodes.json
  - feature_extractor runs in production
  - signals matched against barcodes
  - high-conviction matches surface to PWA with full reasoning

Production integration timeline: ~2-3 weeks AFTER Phase 6 complete.

---

## What this plan does NOT include

1. Production scanner_core.py modifications
2. Bridge L1/L2 composer extensions
3. brain.py scoring layer build
4. PWA integration
5. Paper-trade infrastructure for existing INV-006/INV-012 findings
6. Live deployment of barcodes.json

These are separate workstreams handled after Phase 6 complete.

---

## Safety nets

If at any phase the user's confidence drops:
- HALT immediately
- Document state in lab/AUTO_RUN_STATUS.md
- Allow user to redirect / scope down / abandon

If a phase produces unexpected output:
- HALT
- Surface to user for diagnosis
- Do not proceed to next phase

If validation gate fails:
- HALT
- Re-do current phase with corrections
- Do not proceed

---

## Expected timeline

| Phase | Duration |
|---|---|
| Phase 1 | 1-2 weeks (feature library design + build + validation) |
| Phase 2 | 3-5 days (importance analysis) |
| Phase 3 | 3 days (baselines) |
| Phase 4 | 2 weeks (combination engine + walk-forward) |
| Phase 5 | 3-5 days (live validation) |
| Phase 6 | 3-5 days (barcode compilation) |

**Total:** ~6-8 weeks of Lab work

---

## Sign-off

- This plan authored 2026-05-XX by user + Claude.
- User has reviewed and approved structure.
- Each phase will be executed in dedicated CC session.
