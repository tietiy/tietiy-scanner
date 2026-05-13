# Regime Detector v2 — Master Design

**Generated:** 2026-05-13 (design only — no code, no production changes)
**Sub-files:** [01_problem_statement](01_problem_statement.md) · [02_state_space](02_state_space.md) · [03_input_features](03_input_features.md) · [04_decision_logic](04_decision_logic.md) · [05_validation](05_validation.md) · [06_implementation_plan](06_implementation_plan.md) · [07_integration_points](07_integration_points.md) · [08_risks_and_questions](08_risks_and_questions.md)

---

## PART 10 — The One Sentence Summary

**Replace TIE TIY's 3-state regime classifier (Bull / Bear / Choppy) — currently single-input, weekly-cadence, and demonstrably stale by 5–10 days while losing money on misclassified Choppy signals — with a 5-state classifier (Bull / Bull-Recovery / Choppy / Bear-Recovery / Bear), rule-based across 9 inputs (Nifty trend + position + vol + VIX), validated by re-labeling the historical 281 resolved signals and confirming that UP_TRI×Bear's proven 94.7% WR n=96 cohort preserves to ≥85% WR in Bear-family states; ~50 hours / 3 weeks; ships only after a signed promotion memo following 5 gating validations.**

---

## PART 1 — Problem statement (one-page summary; full at [01](01_problem_statement.md))

**Five failure modes of the current classifier (`scanner/main.py:get_nifty_info()` lines 257-337):**

1. **F1 — Choppy is a catch-all** collapsing 4 distinct micro-states (distribution-top, post-Bear recovery, Bull-flat, Bear-flat) into one label with different forward-return distributions.
2. **F2 — Brain reads a weekly snapshot.** `brain_derive._derive_regime_watch()` pulls regime from `weekly_intelligence_latest.json` (rewritten Sun 20:00 IST only). Today's brain reads a label from 2026-05-08 while Nifty fell -3.3% in 2 days.
3. **F3 — Slope threshold ±0.005 misclassifies recovery.** The Apr-26 weekly snapshot (slope=+0.0036, ret20=+7.38%, above_ema50=True) was clearly recovering market, labeled Choppy.
4. **F4 — Asymmetric predictive power.** Bear label is gold (UP_TRI×Bear 94.7% WR n=96; BULL_PROXY×Bear 87.5% n=16). Choppy is anti-predictive (every signal type loses).
5. **F5 — Single-input, single-bar.** Uses only Nifty close. Ignores VIX, EMA20, EMA200, realized vol, Bank Nifty.

**Operational impact today (2026-05-13):**
- Nifty fell from 24176 → 23379 in two trading days (-3.3%). `above_ema50` flipped True→False on 2026-05-12. `ret20_pct` went from +1.69 to -1.94.
- Brain still reports "Choppy stable 7 days" (Sunday's label).
- 80 PENDING signals, none tagged Bear (the regime where 94.7% WR fires).
- Today's 8 signals all bucketed SKIP.

**Why FINAL_SYNTHESIS Day 2 + Day 3 fixes are insufficient:** they add one Bull label + daily refresh on the same broken 3-bin grid. They patch staleness and the recovery edge case but do not fix granularity (F1, F4) or single-input (F5).

---

## PART 2 — Design goals (see [02](02_state_space.md), [03](03_input_features.md), [04](04_decision_logic.md))

The v2 classifier must:
1. **Capture market state with enough granularity** that UP_TRI×Choppy (anti-predictive) and UP_TRI×Bear (94.7% WR) cannot collapse into the same label.
2. **Update daily** with a same-day label (no weekly staleness).
3. **Detect regime TRANSITIONS** via `regime_pending` + `confidence_pending` fields, so brain can warn the operator before a label commits.
4. **Preserve UP_TRI×Bear edge attribution** — ≥80% of historical Bear signals stay in Bear-family (Bear OR Bear-Recovery), WR stays ≥85%.
5. **Auditable** — every label explainable via which of 5 named gates fired.
6. **Testable** — every label verifiable against historical Nifty data via the cohort preservation harness.

---

## PART 3 — State space (full at [02](02_state_space.md))

**5 states:**

| State | Definition | Quantitative gate |
|---|---|---|
| **Bull** | Steady-state Bull, low vol | above_ema50 ✓ ; above_ema200 ✓ ; slope > 0.005 ; ret20 > 0 ; vix < 18 |
| **Bull-Recovery** | Cleared EMA50, vol compressing | above_ema50 ✓ ; slope > 0, ≤ 0.005 ; ret20 > 3 ; vix < 20 |
| **Choppy** | Residual; no directional persistence | None of the above match |
| **Bear-Recovery** | Below EMA50, slope rising | above_ema50 ✗ ; slope > 0 ; ret20 > 0 |
| **Bear** | Steady-state Bear, vol elevated | above_ema50 ✗ ; above_ema200 ✗ ; slope < -0.003 ; ret20 < -2 ; vix > 18 |

**Persistence rules:**
- 3-day confirmation for Bull / Bear / Choppy
- 2-day confirmation for Recovery states
- Whipsaw guard: 3+ transitions in 10 days → force Choppy for next 5 days

**Allowed transitions** form a DAG: cannot jump Bull → Bear or Bear → Bull directly. Must pass through Recovery + Choppy states.

**Why 5 (not 3 or 7):** 5 preserves consultant's Bear-only deployment without inflating cohort cells past n<10. 3-state is broken (current). 7-state pushes too many cells below validation sample size.

---

## PART 4 — Input features (full at [03](03_input_features.md))

**9 required inputs (all from yfinance, no external APIs):**

| # | Feature | Source |
|---|---|---|
| F1 | Nifty close | `^NSEI` |
| F2 | EMA50 10-bar slope | derived |
| F3 | above EMA50 | derived |
| F4 | ret20% | derived |
| F5 | above EMA20 | derived |
| F6 | above EMA200 | derived (needs 1y lookback — current is 3mo) |
| F7 | 20-day realized vol | derived |
| F8 | India VIX | `^INDIAVIX` (NEW) |
| F9 | VIX 10-day change | derived from F8 |

**Deferred to v2.1:** Bank Nifty relative strength (F10). **Deferred to v3+:** USDINR, 10Y yield, breadth, FII/DII, global context.

Output schema: `output/regime_features.json` — new file, written by extended `_log_regime_debug()` in main.py.

---

## PART 5 — Decision logic (full at [04](04_decision_logic.md))

**Rule-based** — 5-gate decision tree, priority order: Bull → Bear → Bull-Recovery → Bear-Recovery → Choppy (residual). First match wins. Plus persistence layer + allowed-transition enforcement.

**Why not ML:** auditable, no training data needed, consultant-aligned, reversible in one config flag, no operational maintenance burden. Hybrid rule+ML deferred to v3.

**Threshold calibration:** initial values in `04_decision_logic.md §"Why these specific thresholds"`. Tuned during validation (up to 3 iterations) before promotion.

---

## PART 6 — Validation methodology (full at [05](05_validation.md))

**Six validations. Five are gating. All must pass before promotion.**

### V1 — Cohort Preservation Test (CRITICAL)
Re-label all 281 resolved signals under v2. Pass criteria:
- **C1:** ≥80% of UP_TRI×Bear historical signals stay in Bear-family (≥77 of 96)
- **C2:** WR of UP_TRI ∩ Bear-family under v2 ≥85%
- **C3:** Signals that moved OUT have a regime-transition explanation
- **C4:** New UP_TRI × Bull-Recovery cohort: either n<5 (no false attribution) or WR>60% (legitimate new cohort)
- **C5:** 100% regime label coverage (no NaN)

**Effort:** 4 hours.

### V2 — Visual Sanity Check
Plot 60-day Nifty + v2 regime bands. Operator inspects for 10 min. PASS if labels visually align with market state.

**Effort:** 2.5 hours.

### V3 — Transition Reasonableness
Count v2 transitions over last 12 months. Pass criteria:
- **T1:** 6 ≤ transitions ≤ 20 in 12 months
- **T2:** ≥75% of hand-curated known inflection points captured within ±5 trading days
- **T3:** ≤20% false (immediately-reversing) transitions

**Effort:** 6 hours.

### V4 — Side-by-Side Shadow Run (2 weeks / 10 trading days)
Run v2 in parallel with v1. Production continues using v1. Pass criteria:
- **S1:** agreement rate informational (50-80% expected)
- **S2:** ≥1 case v2 catches transition v1 missed (proves v2 adds value)
- **S3:** zero cases v1 catches transition v2 missed (proves v2 doesn't regress)
- **S4:** ≤1 nonsense day in 10

**Effort:** 6 work hours + 10 calendar days elapsed.

### V5 — Cohort-Wise Predictive Power
For each (signal_type × v2_regime) cell, recompute WR. Pass criteria:
- **P1:** lower intra-cohort variance vs v1
- **P2:** all known winners preserved (UP_TRI×Bear 94.7%, BULL_PROXY×Bear 87.5%, UP_TRI×Metal 88.2%)
- **P3 (bonus):** at least one new candidate positive cohort identified
- **P4:** DOWN_TRI failure preserved (no false signal that DOWN_TRI is fixable)

**Effort:** 3 hours.

### V6 — Rollback Trigger Memo
Pre-committed list of hard-reject triggers (R1-R5) and soft retune triggers (R6-R8). Signed memo at `doc/regime_v2_design/promotion_decision_<date>.md` before flip.

**Effort:** 1 hour.

### Total validation effort
~23 hours of work + 10-day shadow window.

### Hard rollback triggers (REJECT v2)
- R1: Validation 1 fails (Bear-family preservation < 80%)
- R2: V3 T2 fails (<75% inflections caught)
- R3: V4 S3 ≥ 1 (v2 missed a transition)
- R4: V4 S4 > 1 (v2 nonsense > 1 in 10 days)
- R5: V5 P2 fails (proven winners not preserved)

### Soft retune triggers (tune + retry, max 3 iterations)
- R6: V1 partial fail (preservation 70-80%) → loosen Bear gate
- R7: V3 T1 too few (<6) → loosen persistence
- R8: V3 T1 too many (>20) → tighten persistence

---

## PART 7 — Implementation plan (full at [06](06_implementation_plan.md))

| Phase | Description | Hours | Calendar |
|---|---|---:|---|
| 1 | Encode classifier (`regime_classifier_v2.py` NEW, extend `main.py`) | 12-16 | 2-3 evenings |
| 2 | Backfill historical labels (281 signals) | 6-8 | 1 day |
| 3 | Validation V1-V3 + V5 (offline scripts + operator review) | 12-15 | 2 days |
| 4 | Side-by-side shadow deployment | 6 + 10 calendar days | 2 weeks elapsed |
| 5 | Promote to authoritative (brain_derive, scorer, bridge, mini_scanner) | 8-10 | 1 day |
| **Total** | | **44-55 hours** | **~3 calendar weeks** |

**~1,000 LOC new + ~200 LOC modified** across ~12 files.

**Reversibility:** `scanner/config.py:USE_REGIME_V2 = False` flag reverts all consumers to v1. Promotion is NOT a point of no return.

---

## PART 8 — Integration points (full at [07](07_integration_points.md))

**14 regime consumers/writers identified.** Primary changes:

1. `scanner/main.py:get_nifty_info()` — extend (Phase 1).
2. `scanner/regime_classifier_v2.py` — NEW module (Phase 1).
3. `scanner/brain/brain_derive.py:_derive_regime_watch()` — read v2 file (Phase 5). **This is the L2 leverage point from `doc/tietiy_mindmap/MASTER_MINDMAP.md`.**
4. `scanner/scorer.py` — add scoring for Bull-Recovery / Bear-Recovery (Phase 5).
5. `scanner/bridge/composers/*` — read v2 from bridge_state (Phase 5).
6. `scanner/bridge/queries/q_regime_baseline.py` — query on v2 field (Phase 5).
7. `scanner/journal.py` — schema v6 adds `regime_v2` field (Phase 5).
8. `scanner/brain/brain_reason.py:_run_regime_shift_detector()` — use `regime_pending` context (Phase 5).
9. `data/mini_scanner_rules.json` — review regime gates; existing `regime=Bear` rules continue to match v2 Bear.

**Backward-compat during shadow:** production reads v1, v2 written in parallel.
**Backward-compat post-promotion:** historical signals retain v1 `regime`; new signals get both `regime` (= v2) and `regime_v2` (= v2) — gives 6 months for cohort taxonomies to converge.

---

## PART 9 — Risks & open questions (full at [08](08_risks_and_questions.md))

### Risks (5)

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | v2 kills UP_TRI×Bear cohort attribution | **CRITICAL** | Validation 1 + threshold retune + forward-only attribution |
| 2 | Too many transitions / year (noisy) | MEDIUM | Persistence rules + whipsaw guard + V3 T1 ≤ 20 |
| 3 | Too few transitions (over-smoothed) | MEDIUM | V3 T1 ≥ 6, retune if fail |
| 4 | VIX fetch fails | LOW | Graceful degradation; 3-day cache; alert |
| 5 | Consultant guidance contradicts v2 | HIGH | sub_regime stays in shadow_ops scope; consultant review before Phase 5 |

### Open questions (5) — for user to decide before build starts

| Q | Question | Recommendation |
|---|---|---|
| Q1 | State granularity: 5 or 7? | **5** |
| Q2 | Methodology: rule-based or hybrid? | **Rule-based** |
| Q3 | Cohort-WR drift tolerance (Bear-family WR threshold)? | **≥85%** (≤10pp drop) |
| Q4 | Shadow run duration: 1, 2, or 4 weeks? | **2 weeks** |
| Q5 | sub_regime: include in v2 or defer to v3? | **Defer to v3** |

---

## PART 10 — The One Sentence Summary (restated)

**v2 replaces a single-input weekly-stale 3-state regime classifier with a 9-input daily-refreshed 5-state classifier, validated by preserving UP_TRI×Bear's 94.7% WR cohort to ≥85% under re-labeled history, shipped only after 5 gating validations and a signed promotion memo, totaling ~50 hours over 3 weeks with one-flag reversibility.**

---

## What this design is and is not

### IS
- A 5-state classifier (Bull / Bull-Recovery / Choppy / Bear-Recovery / Bear)
- A rule-based decision tree with persistence + transition enforcement
- A daily-refreshed alternative to the weekly snapshot brain currently reads
- A validation harness with explicit pass/fail thresholds
- A 3-week, ~50-hour buildable project
- A foundation that the existing rules + cohorts + bridge + brain layers can absorb without rewrites
- Reversible via one config flag

### IS NOT
- A trading strategy change (existing rules, gates, bucket logic all preserved)
- An ML model (rule-based; ML deferred to v3)
- A 7-state classifier (deferred to v3)
- A sub_regime hot/warm/cold layer (lives in shadow_ops_v1; v2 doesn't touch it)
- A PWA update (separate Stage 2 Day 4 effort)
- A retroactive rewrite of signal_history (forward-only v2 attribution + separate annotation file for backfill)
- A consultant-bypass (consultant guidance preserved; sub_regime deferred respects their framing)

---

## What to do next

1. **Read this document and the 8 sub-files** (tomorrow morning with coffee).
2. **Answer the 5 open questions** in `08_risks_and_questions.md`.
3. **Approve / modify / reject** the design.
4. If approved: schedule the 3-week implementation (Phase 1 first evening, Phase 4 starts at end of week 2).
5. If modified: list the changes; revise this design before Phase 1 starts.
6. If rejected: alternative path is the FINAL_SYNTHESIS Stage 2 Day 2 + Day 3 surgical patches only (lower investment, lower payoff).

**No production code touched. No data changed. This is design only.**
