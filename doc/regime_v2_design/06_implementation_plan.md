# 06 — Implementation Plan

## Total effort

| Phase | Description | Hours | Calendar |
|---|---|---:|---|
| Phase 1 | Encode classifier | 12-16 | 2-3 evenings |
| Phase 2 | Backfill historical labels | 6-8 | 1 day |
| Phase 3 | Validation V1-V3 + V5 (offline) | 12-15 | 2 days |
| Phase 4 | Side-by-side shadow deployment | 6 work + 10 calendar days | 2 weeks elapsed |
| Phase 5 | Promote to authoritative | 8-10 | 1 day |
| **Total** | | **44-55 hours** | **~3 calendar weeks** |

Inside the user's stated 45-65 hour envelope. Aligned with the "design tomorrow morning Abhishek reads with coffee" constraint — this is a 3-week project, not a 3-month one.

---

## Phase 1 — Encode classifier (12-16 hours)

### Files touched
- `scanner/main.py` — extend `get_nifty_info()` to write F1-F9 features + v2 regime
- `scanner/regime_classifier_v2.py` (NEW) — gate logic + persistence + transition checks
- `scanner/main.py:_log_regime_debug()` — extend to log v2 features alongside v1

### Tasks
1. (~2h) Extend yfinance pull: `period='3mo'` → `'1y'`. Pull `^INDIAVIX` alongside `^NSEI`. Handle missing-VIX gracefully.
2. (~3h) Compute features F5-F9: EMA20, EMA200, realized vol, VIX level, VIX 10-day change.
3. (~3h) Implement 5-gate decision tree in new module `scanner/regime_classifier_v2.py`. Function signature: `classify_v2(features: dict, prior_state: dict) -> dict` returning `{regime, regime_pending, confidence_pending, gate_fired, warnings}`.
4. (~3h) Implement persistence logic (3-day confirm for Bull/Bear/Choppy, 2-day for Recoveries, whipsaw guard).
5. (~2h) Wire `_log_regime_debug` to write extended schema to `output/regime_features.json` (parallel to existing `regime_debug.json`).
6. (~2h) Tests: unit tests for each gate, transition logic, persistence. Synthetic feature inputs.

### Success criterion
`python -m scanner.main run_morning_scan` (or equivalent test invocation) writes `regime_features.json` with all 9 features + v2 regime + prior_state correctly tracked.

### Files NOT touched in Phase 1
- `scanner/brain/brain_derive.py` — stays reading `weekly_intelligence_latest.json`
- `scanner/bridge/composers/*` — no changes
- `data/mini_scanner_rules.json` — no changes
- `output/weekly_intelligence_latest.json` — continues to be written by `weekly_intelligence.py`

This is the **parallel writer** phase: v2 emits labels but nobody consumes them yet.

---

## Phase 2 — Backfill historical labels (6-8 hours)

### Goal
Re-classify every trading day from 2024-01-01 to 2026-05-13 using v2. This enables Validations 1, 3, 5.

### Files touched
- `scripts/backfill_regime_v2.py` (NEW) — one-shot script
- `output/regime_v2_history.json` (NEW) — output: per-day labels for the backfill window

### Tasks
1. (~1h) Bulk yfinance pull: `^NSEI` and `^INDIAVIX` from 2024-01-01.
2. (~2h) Compute features for every day. Cache to `output/regime_v2_features_daily.csv` for the validation phase.
3. (~2h) Run classifier day-by-day, maintaining prior_state. Output: timeline of regime labels.
4. (~1h) Cross-check: count days per regime, plot regime-share over time. Sanity verify the distribution (e.g., ~12% Bear days expected per consultant Round 9 §6.2).
5. (~1h) Augment `output/signal_history.json` records with `regime_v2` field via separate file (not mutating signal_history) — `output/signal_history_v2_annotated.json`.

### Success criterion
Every of the 281 resolved signals has a v2 regime label. Distribution of v2 regime labels reported.

### Reversibility
This phase only WRITES new files (`regime_v2_*.json`). It does NOT modify `signal_history.json` or any existing file. Reversion = `rm` the new files.

---

## Phase 3 — Validation V1-V3 + V5 offline (12-15 hours)

### Files touched
- `scripts/validate_regime_v2.py` (NEW) — runs all offline validations
- `doc/regime_v2_design/validation_results_<date>.md` (NEW) — output report

### Tasks
1. (~4h) **Validation 1** — Cohort Preservation Test. Script reads `signal_history.json` + `regime_v2_history.json`. Outputs cohort table per signal_type × v2_regime. Computes C1-C5 pass/fail.
2. (~2h) **Validation 2** — Visual Sanity Check. Matplotlib chart Nifty + v2 bands for last 60 days. Save as `doc/regime_v2_design/sanity_plot.png`. Operator review (0.5h).
3. (~3h) **Validation 3** — Transition Reasonableness. Hand-curate `doc/regime_v2_design/known_inflections.md` listing 10-15 known regime events 2025-05-01 to 2026-05-01. Script computes T1, T2, T3.
4. (~3h) **Validation 5** — Cohort-Wise Predictive Power. Re-aggregate cohort stats under v2. Compare against v1 baselines. Compute P1-P4.
5. (~1h) Write validation report to `doc/regime_v2_design/validation_results_<date>.md` with PASS/FAIL per validation + threshold-tuning recommendations.

### Iteration loop
If any of V1, V3, V5 fail soft (R6, R7, R8 per `05_validation.md §"Soft rollback triggers"`):
- Tune thresholds in `04_decision_logic.md` (e.g., slope threshold for Bear, persistence days).
- Re-run Phase 2 backfill (~1h).
- Re-run Phase 3 validation (~3h for partial; ~12h for full).
- Cap at 3 iterations before hard reject.

### Success criterion
Validation report shows PASS or PASS-WITH-TUNED-THRESHOLDS on V1, V3, V5. V2 passes operator review.

---

## Phase 4 — Side-by-side shadow deployment (6 work hours + 10 calendar days)

### Files touched
- `scanner/main.py` — already writes both v1 (existing) and v2 (Phase 1) labels.
- `scripts/regime_v2_shadow_monitor.py` (NEW) — daily comparison script, runs alongside morning_scan
- `doc/regime_v2_design/shadow_log_<date>.md` (NEW) — daily comparison log

### Tasks
1. (~2h) Add a daily check at end of morning_scan: compare v1.regime vs v2.regime. Log to `shadow_log_<date>.md`.
2. (~2h) Each day during the 10-day window: operator reviews the daily log for 5-10 minutes. Notes which classifier is "right" with hindsight (often only knowable in hindsight from next 2-3 days).
3. (~2h) Day 11: compile final shadow log, compute S1-S4 metrics per `05_validation.md §"Validation 4"`.

### Success criterion
S2 ≥ 1, S3 = 0, S4 ≤ 1 per Validation 4 pass criteria.

### What happens during shadow
- Production continues using v1 regime label. Brain, bridge, mini_scanner all unchanged.
- Operator monitors v2 quality.
- If v2 misclassifies, no production impact — just a logged "v2 disagrees" event.

---

## Phase 5 — Promote to authoritative (8-10 hours)

After all validations pass + promotion memo signed:

### Files touched
- `scanner/brain/brain_derive.py` — change `_derive_regime_watch()` to read `regime_features.json` (or `regime_v2_history.json` for historical days) instead of `weekly_intelligence_latest.json`
- `scanner/bridge/composers/premarket.py`, `postopen.py`, `eod.py` — update regime references (if direct reads exist)
- `scanner/bridge/queries/q_regime_baseline.py` — update to v2 regime field on signals
- `data/mini_scanner_rules.json` — update boost rules: `regime=Bear` → keep (matches v2 Bear); consider whether to add `regime=Bear-Recovery` rules
- `scanner/weekly_intelligence.py` — note: this still runs weekly but no longer authoritative for brain
- `output/weekly_intelligence_latest.json` — continues to be written but brain ignores it

### Tasks
1. (~2h) Add `regime_v2` field to signal_history records (forward-only — new signals get v2 tag from scan day; historical 281 signals remain with v1 tag + v2 annotation in separate file from Phase 2).
2. (~3h) Update `brain_derive.py:_derive_regime_watch()` to read `regime_features.json`. Keep weekly_intel as fallback for one week post-promotion.
3. (~2h) Update mini_scanner_rules.json: review each rule's regime gate. Decide:
   - `regime=Bear` → stays (v2 `Bear` matches)
   - Consider adding `regime=Bear-Recovery` boost candidates if Validation 1 surfaced one
4. (~2h) Update bridge composer reads. Verify bucket_engine Gate 4 reads new regime correctly.
5. (~1h) Final smoke test: run morning_scan, verify brain output uses v2 regime.

### Reversibility plan
- Keep v1 classifier code path active for 30 days post-promotion.
- One-line config flag (`USE_REGIME_V2 = False` in `scanner/config.py`) reverts all consumers to v1.
- If rollback needed: flip flag, restart cron schedule, problem resolved within 24 hours.

### Success criterion
- Day after promotion: brain's `regime_watch.json` reports v2 label.
- Bridge briefs use v2 label.
- mini_scanner_rules apply correctly under v2 regime tags.

---

## What's explicitly NOT in this plan

- **No PWA / dashboard updates.** Per `doc/FINAL_SYNTHESIS.md` Stage 2 Day 4, PWA bridge_state integration is a separate Stage 2 effort. Regime label in PWA can come later.
- **No ML refinement.** Hybrid rule+ML is v3.
- **No 7-state expansion.** v3.
- **No Bank Nifty integration (F10).** v2.1 if v2 succeeds.
- **No retroactive cohort rebuild in signal_history.json.** v2 attribution is forward-only; backfill goes into a separate annotation file.

## Effort breakdown by skill type

| Skill | Hours |
|---|---|
| Python coding (scanner module, scripts) | ~25h |
| Data analysis (validation scripts, cohort) | ~10h |
| Operator review (visual sanity, shadow monitoring) | ~5h |
| Documentation (validation report, promotion memo) | ~3h |
| Cron / deployment / integration | ~5h |

The bulk is Python coding for the classifier + validation. The operator-review steps are essential but bounded.

## Effort confidence

- Phase 1 (12-16h): **HIGH confidence**. Well-scoped, similar in scale to past brain modules.
- Phase 2 (6-8h): **HIGH confidence**. Backfill scripts are standard.
- Phase 3 (12-15h): **MEDIUM confidence**. Iteration loop could blow up the budget if initial thresholds fail multiple tests. Cap iteration at 3 cycles.
- Phase 4 (6h work + 10 calendar days): **MEDIUM confidence**. Requires daily operator attention for 2 weeks — historically a weakness for this operator.
- Phase 5 (8-10h): **HIGH confidence**. Mechanical integration.

**Worst case (1.5x estimate)**: 66-82 hours over 5-6 calendar weeks. **Best case (0.8x estimate)**: 35-44 hours over 2.5 weeks. **Realistic plan: 45-55 hours over 3 weeks.**
