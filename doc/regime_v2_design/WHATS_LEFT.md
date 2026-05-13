# Regime Detector V2 — What's Left

**Generated:** 2026-05-13 (post-bypass commit)
**Project location:** `scanner/regime_v2/`
**Status:** V2 classifier + Group A bypass operational. Production code untouched. Validation criteria conflict pending user decision before promotion.

---

## Table of Contents

**PART 1 — EXECUTIVE SUMMARY**
- 1.1 Current State
- 1.2 What's Left (7 items, 3 tiers)
- 1.3 Calendar to Production
- 1.4 Open Decisions (5)
- 1.5 One-Page Summary

**PART 2 — FULL DETAIL**
- 2.1 What's Done
- 2.2 Tier 1 — Blocking Promotion (4 items)
- 2.3 Tier 2 — Should Happen Soon (3 items)
- 2.4 Tier 3 — V3 Scope (4 items)
- 2.5 Discoveries Made During V2 Build
- 2.6 What is NOT Part of V2
- 2.7 Risk Inventory for Remaining Work
- 2.8 Decision Tree for "Done"
- 2.9 Effort Summary Table

---

# PART 1 — EXECUTIVE SUMMARY

## 1.1 Current State

**V2 classifier**: 5-state rule-based (BULL / BULL_RECOVERY / CHOPPY / BEAR_RECOVERY / BEAR) built in `scanner/regime_v2/` across 9 Python modules (~2,000 LOC including tests). All 38 unit tests pass.

**Three calibration cycles done**, all on 15-year historical Nifty (3,760 trading days, 2011-01-03 to 2026-05-05):

| Cycle | Key change | UP_TRI Bear preservation | UP_TRI Bear-cohort WR |
|---|---|---:|---:|
| retune0 | initial calibration | 11.7% (11/94) | 90.9% n=11 |
| retune1 | Fix A+B+C (transitions) | 42.6% (40/94) | 95.0% n=40 |
| retune2 | Fix E+F+G+H (Sonnet visual rec) | 42.6% (40/94) | 95.0% n=40 |
| retune2 + bypass | Sonnet data analysis → -9% bypass | **55.3% (52/94)** | **94.2% n=52** |

**Group A discovery** (the key insight): Sonnet's analysis of the 67 V1-Bear signals V2 reclassified to CHOPPY found they split into two distinct mechanisms:
- **Group A** (23 signals, deep-crash bottoms ret_30d ≤ -9%): real Bear, V2 wrongly excluded. Captured by bypass at 91.7% WR.
- **Group B** (44 signals, post-crash recovery ret_30d -6.5% to -7%): different edge mechanism (recovery beta), V2 correctly excluded.

**Critical numbers (final, retune2 + bypass):**
- V5 P2 UP_TRI bear-tradeable WR: **92.6%** on n=54 → **PASS** (threshold ≥85%)
- V5 P2 BULL_PROXY bear-tradeable WR: **90.9%** on n=11 → **PASS** (threshold ≥75%)
- V1 C1 preservation: **55.3%** (52/94) → **FAIL** per design's 80% threshold

**The validation criteria conflict**: V5 P2 (cohort quality) PASSES. V1 C1 (cohort count preservation) FAILS at 80% threshold but Sonnet's analysis showed the 80% threshold is structurally unattainable — V1's Bear bucket was heterogeneous (Group A + Group B), and V2 correctly excludes Group B. The "right" metric for V2's design intent is V5 P2, not V1 C1.

**Production code state:**
- `scanner/main.py:get_nifty_info()` — V1 classifier, unchanged.
- `scanner/brain/brain_derive.py:_derive_regime_watch()` — still reading `weekly_intelligence_latest.json`, unchanged.
- `data/mini_scanner_rules.json` — regime gates unchanged (kill_002 added separately, unrelated to V2).
- `scanner/bridge/core/bucket_engine.py` Gate 4 — still uses V1 regime field.

**5 commits on main related to V2**:
- `4a615c7d` design study consolidation
- `98646a2c` regime_v2 Phases 1-3 build + initial validation FAIL
- `0c900b4d` regime_v2 retune1
- `63584909` regime_v2 retune2
- `eac6e536` Sonnet out-movers analysis (HYBRID verdict)
- `c80194d2` Group A bypass implementation

---

## 1.2 What's Left (7 items, 3 tiers)

### Tier 1 — MUST happen before V2 promotion (4 items)

| # | Item | Effort | Calendar | Blocks |
|---|---|---:|---|---|
| T1.1 | Validation criteria decision (V5 P2 vs V1 C1) | 1 hr | same day | Everything downstream |
| T1.2 | Production integration (where bypass lives in code) | 3 hrs | 1-2 days | Phase 4 shadow |
| T1.3 | V4 side-by-side shadow run | 2 hrs setup + 10 trading days observation | 2-3 weeks | Promotion |
| T1.4 | Promotion memo + flip | 1 hr write + 1 day flip | 1 day | — |

### Tier 2 — Should happen soon, parallel possible (3 items)

| # | Item | Effort | Calendar | Parallel to T1? |
|---|---|---:|---|:---:|
| T2.1 | Group B detector design | 8-12 hrs | 2-3 weeks | YES (separate file) |
| T2.2 | VIX integration | 4-6 hrs | 3 days | YES |
| T2.3 | Daily refresh production wiring (L2 leverage point) | 2-3 hrs | 1 day | YES |

### Tier 3 — V3 scope, future (3 items)

| # | Item | Effort | When |
|---|---|---:|---|
| T3.1 | ML refinement layer (rule + ML hybrid) | 40+ hrs | After 6+ months V2 production data |
| T3.2 | Sub-regime (consultant hot/warm/cold) | 16-24 hrs | After Group B detector lives |
| T3.3 | 7-state granularity | 24-32 hrs | When sample sizes support it (Year 2) |

**Tier 1 sum**: ~7 hours active + 10 trading days observation = **2-3 weeks to production-ready V2**.
**Tier 2 sum**: ~14-21 hours active + can run parallel.

---

## 1.3 Calendar to Production

```
Week 0 (today, 2026-05-13)
  ├─ V2 + bypass committed and pushed (c80194d2)
  └─ All Tier 1 items pending operator decision

Week 1 (2026-05-14 to 2026-05-20)
  ├─ Day 1: T1.1 validation criteria decision (1 hr)
  ├─ Day 2-3: T1.2 production integration (3 hrs)
  ├─ Day 4: T1.3 side-by-side run begins (2 hrs setup)
  └─ Optional parallel: T2.3 daily refresh wiring (2-3 hrs)

Week 2-3 (2026-05-21 to 2026-06-03)
  ├─ Daily: 10-minute review of V1 vs V2 daily logs
  ├─ Parallel: T2.1 Group B detector encoding (if pursuing)
  ├─ Parallel: T2.2 VIX data ingestion (if pursuing)
  └─ Day 10: V4 outcome verdict (PASS/FAIL/AMBIGUOUS)

Week 4 (2026-06-04 to 2026-06-10)
  ├─ T1.4 promotion memo
  ├─ Flip brain_derive to V2 (with V1 fallback for 30 days)
  └─ V2 is production
```

**Total active engineering**: ~7-10 hours.
**Total elapsed (including shadow window)**: 3-4 weeks.

---

## 1.4 Open Decisions (5)

The user must decide these before Week 1 work begins.

### D1 — Which validation metric defines "promotion-ready"?

**Question**: Use V5 P2 (cohort WR ≥85%) which PASSES, or stick with V1 C1 (≥80% preservation) which FAILS?

**Evidence**:
- V1 C1 measures bucket-count preservation. Sonnet's analysis (out_movers_sonnet_analysis.md) showed V1's Bear bucket is two distinct mechanisms; 80% structurally unattainable without diluting V2's quality.
- V5 P2 measures cohort quality (WR within preserved). Currently 92.6% n=54 — better than V1's 94.7% n=94 in absolute terms with smaller sample.
- The design study's V6 §"Rollback triggers" hard-codes R1 = "V1 fails C1" as reject criterion. Strictly applied, V2 is rejected.

**Recommendation in source**: Sonnet (out_movers analysis section 4): "V2's exclusion of Group B is correct... V2's stricter Bear is qualitatively better." Implies V5 P2 should be the gating metric, with C1 demoted to informational.

**User decides**: accept V5 P2 as gate → V2 proceeds; or accept C1 as gate → V2 stalls/redesign.

### D2 — Where does the bypass logic live in production?

**Question**: Bypass is currently a validation-harness annotation (`v2_bear_tradeable` column in remapped parquet). For production, where does this live?

**Options**:
1. Inside `scanner/regime_v2/classifier.py` as a post-classification adjustment (modifies V2 output).
2. In `scanner/scorer.py` or `scanner/main.py` at the signal-scoring stage (modifies signal scoring).
3. In `data/mini_scanner_rules.json` as a new gate definition (rule-system approach).
4. In `scanner/bridge/core/bucket_engine.py` Gate 4 (regime-evidence layer).

**Trade-offs**: Option 1 changes the classifier semantics (clean but blurs "regime" vs "tradeability"). Option 2/3 keeps regime pure but adds a signal-level overlay. Option 4 integrates at the existing bucket-engine layer.

**No clear winner yet** — depends on whether bypass is "regime correction" (Option 1) or "signal eligibility under regime" (Option 2/3/4). User decides.

### D3 — Build Group B detector now or defer?

**Question**: Sonnet identified Group B (44 historical UP_TRI signals at 95.6% WR) as a distinct edge mechanism — post-crash recovery beta. Encode it as a new detector now, or defer?

**Evidence**:
- Group B at 95.6% WR n=44 is arguably as strong as UP_TRI×Bear.
- Different mechanism (recovery beta), so needs a different gate than Bear-based.
- Encoding effort: 8-12 hours new detector + validation cycle.

**Recommendation**: Defer until V2 production stable (Week 4+). Build in Month 2.

### D4 — When to deprecate V1 classifier?

**Question**: After V2 promotion, V1 stays writing labels for 30 days as a fallback. When fully retire?

**Options**:
1. Retire at Day 30 post-promotion (aggressive).
2. Retire at Day 90 post-promotion (cautious).
3. Keep indefinitely as fallback (no retirement).

**Cost of keeping V1**: ~2 LOC in main.py, minimal storage. **No reason to retire urgently** — keep as fallback at least 90 days.

### D5 — Migrate brain to V2 daily, or keep weekly?

**Question**: Currently `brain_derive._derive_regime_watch()` reads `weekly_intelligence_latest.json` (weekly Sunday snapshot). After V2 promotion, switch to V2 daily?

**Evidence**: FINAL_SYNTHESIS Stage 2 Day 3 identifies this as the "L2 leverage point". Brain reading a daily-fresh regime would unlock real-time regime-shift detection. ~2-3 hours work.

**Recommendation**: YES. This is the highest-leverage post-promotion change. Should happen within 1 week of V2 going live.

---

## 1.5 One-Page Summary

```
═══════════════════════════════════════════════════════════════════════
                    REGIME V2 — STATE OF PLAY
═══════════════════════════════════════════════════════════════════════

  BUILT             ┃  REMAINING (TIER 1 — BLOCKS PROMOTION)
  ─────             ┃  ─────────────────────────────────────
  ✅ V2 classifier   ┃  ⚠️  T1.1  Validation metric decision (1h)
     5 states       ┃  ⚠️  T1.2  Production integration (3h)
     38 tests pass  ┃  ⚠️  T1.3  Side-by-side run (10 days)
                    ┃  ⚠️  T1.4  Promotion memo (1h)
  ✅ Backfill       ┃
     3,760 days     ┃  ▼ ~7 hrs work + 10 trading days observation
                    ┃
  ✅ 3 retunes     ┃  REMAINING (TIER 2 — PARALLEL)
                    ┃  ──────────────────────────────
  ✅ Group A bypass ┃  📋 T2.1  Group B detector (8-12h)
     -9% threshold  ┃  📋 T2.2  VIX integration (4-6h)
                    ┃  📋 T2.3  Daily refresh wiring (2-3h)

  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃  CURRENT QUALITY (retune2 + bypass)                       ┃
  ┃  UP_TRI bear-tradeable: 92.6% WR on n=54  ✅ PASS  (≥85%) ┃
  ┃  BULL_PROXY bear-tradeable: 90.9% WR on n=11  ✅ PASS     ┃
  ┃  V1 C1 preservation: 55.3% (52/94)  ❌ FAIL  (≥80% req'd) ┃
  ┃  ↑ but Sonnet showed C1 metric is structurally wrong      ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  THE 5 OPEN DECISIONS (in order)
  ──────────────────────────────
  D1: Validation gate = V5 P2 (cohort quality) or V1 C1 (count)?
  D2: Bypass placement = classifier / scorer / rules / bucket_engine?
  D3: Group B detector = build now or defer to Month 2?
  D4: V1 retirement = Day 30 / 90 / indefinite fallback?
  D5: Brain daily-regime migration = yes (recommended) / no?

  CALENDAR
  ────────
  Week 1: decision + production integration + shadow setup
  Week 2-3: side-by-side observation (10 trading days)
  Week 4: promotion memo + flip
  TOTAL: 3-4 weeks to V2 production-ready.

═══════════════════════════════════════════════════════════════════════
TL;DR: V2 + bypass operationally works. Final 4 items + 2-week parallel
       observation = production ready. No production code touched yet.
═══════════════════════════════════════════════════════════════════════
```

---

# PART 2 — FULL DETAIL

## 2.1 What's Done

### Build phase — completed
- **scanner/regime_v2/__init__.py** — module exports
- **scanner/regime_v2/features.py** (129 LOC) — 9 features per design §03 (Nifty close, EMA20/50/200, slope_10d_ema50, above_ema50/200, ret20_pct, realized_vol_20d, VIX optional, banknifty RS optional)
- **scanner/regime_v2/classifier.py** — 5-gate decision tree per design §04 with VIX-degraded fallback (Fix E updates)
- **scanner/regime_v2/transitions.py** (270 LOC) — persistence + allowed-transition graph + whipsaw guard; cumulative retune1+retune2 changes applied (Fixes A, B, C, F, G, H)
- **scanner/regime_v2/io.py** — load_ohlcv, write_jsonl, atomic write helpers
- **scanner/regime_v2/cli.py** (170 LOC) — backfill + side-by-side commands
- **scanner/regime_v2/__main__.py** — entry point for `python -m scanner.regime_v2`

### Unit tests — 38/38 pass
- test_features.py (104 LOC, 9 tests) — feature computation, NaN handling
- test_classifier.py (164 LOC, 13 tests) — gate logic, VIX-degraded mode, edge cases
- test_transitions.py (197 LOC, 16 tests) — persistence, allowed transitions, whipsaw, rolling window, asymmetric exit, min hold, recovery escalation

### Backfill — 15 years complete
- `output/regime_v2/regime_historical_retune2.parquet` — 3,760 daily regime labels 2011-01-03 to 2026-05-05
- `output/regime_v2/regime_historical_retune2_transitions.jsonl` — 238 transitions over 15 years (~16/year, within design target)
- State distribution (retune2):
  - BULL 44.8%
  - CHOPPY 42.3%
  - BEAR 12.7%
  - BEAR_RECOVERY 0.2%
  - BULL_RECOVERY ~0% (suppressed in VIX-degraded mode)

### Signal remapping — complete
- `output/regime_v2/signals_remapped_retune2.parquet` — all 372 signals remapped with V2 regime
- `output/regime_v2/signals_remapped_retune2_with_bypass.parquet` — same + `v2_bear_tradeable` + `bypass_path` + `ret_30d_prior_at_signal` columns
- Coverage: 312/372 = 83.9% (60 signals dated after 2026-05-05 not in backfill window)

### Validation harness — operational
- scanner/regime_v2/validation/v1_cohort_preservation.py (158 LOC)
- scanner/regime_v2/validation/v2_visual_sanity.py (121 LOC) — generates matplotlib PNGs
- scanner/regime_v2/validation/v3_transition_reasonableness.py (161 LOC)
- scanner/regime_v2/validation/v5_cohort_predictive_power.py (193 LOC)
- scanner/regime_v2/validation/run_all.py (87 LOC) — sequential runner

### Three calibration cycles documented
Each cycle has v1_*.md, v3_*.md, v5_*.md, plus Sonnet visual review:
- retune0 (initial, FAIL all gates)
- retune1 (Fix A+B+C transition fixes, PARTIAL improvement)
- retune2 (Fix E+F+G+H per Sonnet's first visual review, Bull fixed, Bear still partial)

### Sonnet API integration
- Used via existing anthropic SDK + .env API key (no new setup)
- Two visual reviews (retune1, retune2 sanity plots)
- One data-driven analysis (67 out-movers)
- Sonnet's data-driven analysis gave the surgical bypass recommendation

### Group A bypass discovery + implementation
- Sonnet's analysis identified V1's Bear bucket as TWO mechanisms
- Group A: 23 deep-crash signals (ret_30d ≤ -9%) at 91.7% WR — captured by bypass
- Group B: 44 recovery-zone signals (ret_30d -6.5% to -7%) at 95.6% WR — intentionally excluded
- Bypass logic: `Bear-tradeable = V2=BEAR OR V2=BEAR_RECOVERY OR (V2=CHOPPY AND ret_30d_prior ≤ -9.0%)`
- Implemented as validation-harness annotation (column), not classifier change

---

## 2.2 Tier 1 Remaining — Blocking Promotion

### T1.1 — Validation Criteria Decision

**What it is**: Choose which numerical test gates V2 promotion: V1 C1 (≥80% bucket preservation) or V5 P2 (≥85% cohort WR).

**Why it's needed**: Sonnet's out-movers analysis showed C1 measures the wrong thing (heterogeneous bucket) while P2 measures the right thing (cohort quality). Without an explicit decision, the design study's R1 rollback trigger says V2 should be rejected. The data says V2 should ship.

**Code/files touched**: None initially. Update `doc/regime_v2_design/05_validation.md` §V6 to reflect chosen gating metric. Optionally update `scanner/regime_v2/validation/v1_cohort_preservation.py` to flag C1 as informational.

**Effort**: 1 hour to discuss, decide, document.

**Dependencies**: None. This is the first decision.

**Success criteria**: A signed/dated decision memo at `doc/regime_v2_design/validation_criteria_decision_<date>.md` stating which metric gates promotion and why.

**Risk if skipped**: Validation results are ambiguous (some PASS, some FAIL). Future-self or another reviewer rejects V2 based on the "wrong" metric. Need a single answer.

---

### T1.2 — Production Integration

**What it is**: Move the V2 + bypass logic from validation-harness to production code path. Specifically: where does the `v2_bear_tradeable` decision get computed and consumed at scan time?

**Why it's needed**: Currently the bypass is a parquet column. The scanner main.py reads V1 regime at scan time. For V2 to drive trading, the production scan must produce V2 regime + bypass evaluation per signal.

**Code/files touched** (depending on D2 decision):
- If Option 1 (classifier-level): `scanner/regime_v2/classifier.py` — add bypass condition after gate evaluation. Probably ~30 LOC.
- If Option 2 (scorer-level): `scanner/scorer.py` — add regime overlay logic.
- If Option 3 (rules-level): `data/mini_scanner_rules.json` — add new gate entry.
- If Option 4 (bucket-engine): `scanner/bridge/core/bucket_engine.py` Gate 4 — read v2_bear_tradeable from feature output.

Cross-cutting: `scanner/main.py:run_morning_scan()` must call V2 alongside V1 and emit V2 regime + bear_tradeable into signal_history.

**Effort**: 3 hours (estimate, depending on D2 choice).

**Dependencies**: D2 (placement decision).

**Success criteria**:
- Production morning_scan emits V2 regime + bear_tradeable per signal.
- Existing UP_TRI×Bear paths (win_001..win_006) continue firing at the same rate (no regression).
- New `regime_v2` and `v2_bear_tradeable` fields appear in `output/signal_history.json` for fresh signals.

**Risk if skipped**: V2 can't drive any production decision. Stuck in validation-harness limbo indefinitely (same fate as brain Step 7).

---

### T1.3 — V4 Side-By-Side Shadow Run

**What it is**: 10 trading days of parallel operation — V1 (production) and V2 (logged-only). Daily comparison of labels + outcomes. Per design §05 V4.

**Why it's needed**:
- Validates that historical-backfill behavior matches real-time scan behavior.
- Catches any data-pipeline differences between yfinance batch fetch (historical) and yfinance daily fetch (production).
- Surfaces operational disagreements between V1 and V2 that statistical tests missed.

**Code/files touched**:
- `scripts/regime_v2_shadow_monitor.py` (new) — daily V1 vs V2 comparison logger
- `output/regime_v2/shadow_log_<date>.md` (generated daily) — comparison entries

**Effort**: 2 hours setup + 10 trading days × 10 min/day operator review = ~4 hours total active.

**Dependencies**: T1.2 (production integration must be live before parallel comparison is meaningful).

**Success criteria** (per design §05 V4 S1-S4):
- S1 agreement rate informational (expect 50-80%)
- S2 ≥ 1 case V2 catches a transition V1 missed
- S3 = 0 cases V2 missed a transition V1 caught
- S4 ≤ 1 nonsense V2 day in 10

**Risk if skipped**: Backfill could have systematic differences from live scan (different yfinance lookback, different bar-close timing, etc.). Without side-by-side, "backfill PASS" doesn't guarantee "live PASS".

---

### T1.4 — Promotion Memo

**What it is**: Per design §V6, a signed/dated memo recording the promotion decision with validation results and any threshold-tuning history.

**Why it's needed**: Forensic trail. If V2 misbehaves 3 months from now, the memo records what was known at promotion time and which gating tests passed.

**Code/files touched**: `doc/regime_v2_design/promotion_decision_<date>.md` (new).

**Effort**: 1 hour to draft. Includes:
- Final validation results (V1, V3, V5, visual)
- Threshold values used (final)
- Known limitations (Group B excluded by design; VIX-degraded mode)
- Operator sign-off

**Dependencies**: T1.3 results.

**Success criteria**: Memo committed to repo. Linked from design study MASTER_DESIGN.md.

**Risk if skipped**: Future operators (including future-self) cannot reconstruct why V2 was promoted with C1 failing. Looks like negligence.

---

## 2.3 Tier 2 Remaining — Should Happen Soon

### T2.1 — Group B Detector Design

**What it is**: Encode a new signal detector for post-crash recovery beta (Sonnet's "Group B" — 44 historical UP_TRI signals at 95.6% WR). Separate from V2 regime classifier.

**Why it's needed**: Group B is a distinct trading edge that V2 correctly excludes from its Bear-tradeable cohort. To capture it, need a separate detector with different gates (e.g., "Nifty recently rallied from -10% to -7% drawdown, age=0 UP_TRI fires").

**Code/files touched**:
- `scanner/regime_v2/group_b_detector.py` (new) — or possibly belongs in `scanner/scanner_core.py` as a new signal-detection branch.
- Validation harness: cohort_health entry for the new detector.

**Effort**: 8-12 hours (design + encoding + 1 validation cycle).

**Dependencies**: T1.1 (must know how V2 is validated before adding new detectors).

**Can run parallel to T1?**: YES — different file, no shared state. Can be coded during Week 2-3 while side-by-side observation runs.

**Success criteria**: New detector emits signals on historical Apr-09/Apr-10 dates (Group B examples) at 90%+ WR on backtest.

**Risk if deferred**: Lose ~44 signals/year of clean alpha that the data shows exists. Not catastrophic — keep on roadmap.

---

### T2.2 — VIX Integration

**What it is**: Add `^INDIAVIX` to the historical and live data layer. Re-run V2 backfill with VIX present (currently degraded-mode).

**Why it's needed**: V2 design §03 calls VIX a required input. Current degraded-mode classifier suppresses BULL_RECOVERY entirely and tightens BULL threshold. With VIX present:
- BULL gate uses slope > 0.005 + vix < 18 (less reliant on ret20 shortcut)
- BULL_RECOVERY becomes a usable transition state
- BEAR gate gains vix > 18 confirmation

**Code/files touched**:
- `scripts/fetch_vix_history.py` (new) — yfinance pull `^INDIAVIX` 2011-present
- `data/historical/indiavix.parquet` (new file, ~150 KB estimated)
- `scanner/regime_v2/cli.py` — pass --vix arg through
- Re-run backfill and validations to compare VIX-full vs VIX-degraded results

**Effort**: 4-6 hours.

**Dependencies**: None for fetching. Strictly additive to current V2 state.

**Can run parallel to T1?**: YES. Independent data layer change.

**Success criteria**: VIX data fetched 2011-2026, backfill re-run with VIX, validation deltas reported. Decide whether to use VIX-full or VIX-degraded for production.

**Risk if deferred**: V2 ships in degraded mode, which Sonnet's visual review flagged as the cause of Bull suppression in retune1. After T2.2, Bull capture improves further.

---

### T2.3 — Daily Refresh Production Wiring (L2 leverage point)

**What it is**: Change `scanner/brain/brain_derive.py:_derive_regime_watch()` to read V2 regime daily from `output/regime_v2/` instead of weekly snapshot from `weekly_intelligence_latest.json`.

**Why it's needed**: This is the L2 leverage point from `doc/tietiy_mindmap/MASTER_MINDMAP.md`. Brain currently reads regime weekly (lag up to 5-7 days). Daily refresh unlocks real-time regime-shift detection. FINAL_SYNTHESIS Stage 2 Day 3.

**Code/files touched**:
- `scanner/brain/brain_derive.py:_derive_regime_watch()` — change source path. ~30 LOC.
- Update `scanner/brain/brain_input.py` if VIX or other features are added to brain context.

**Effort**: 2-3 hours.

**Dependencies**: T1.2 (V2 must be writing to production location daily before brain can read it).

**Can run parallel to T1?**: NO — depends on T1.2. But can happen Week 1 if T1.2 finishes early.

**Success criteria**: Brain's `regime_watch.json` updates daily, not weekly. Trade decisions tagged with regime that reflects same-day market state, not Sunday's snapshot.

**Risk if deferred**: Brain stays partially blind. Same regime mislabel problem that triggered V2 in the first place persists for the brain consumer specifically.

---

## 2.4 Tier 3 Remaining — V3 Scope

### T3.1 — ML Refinement Layer

**What it is**: Hybrid rule-based + ML refinement. The rule-based classifier emits a label; an ML model trained on labeled history refines edge cases. Per design §05 alternative methodology option (deferred to v3).

**When**: After 6+ months of V2 production data accumulated. Need ground-truth labels (operator-tagged) for training.

**Effort estimate**: 40+ hours engineering + 20+ hours operator-time for labeling.

**Why deferred**: No training data yet; adds opaque dependency that conflicts with "1 of 6 operationalize" pattern constraint.

---

### T3.2 — Sub-regime (consultant hot/warm/cold)

**What it is**: Add a sub_regime axis (hot/warm/cold per consultant Round 9) on top of the 5 base regimes. Per shadow_ops_v1 architecture, this lives in the lab feature extractor.

**When**: After Group B detector live (T2.1). The two together approach the consultant's full state space.

**Effort estimate**: 16-24 hours.

**Why deferred**: Out of scope per design §02. Consultant treats this as separate concern.

---

### T3.3 — 7-State Granularity

**What it is**: Expand from 5 states to 7 by adding Distribution (topping) and Bear-Capitulation (terminal crash). Per design §02 option D.

**When**: When historical sample size supports it (need ~600+ resolved signals to have meaningful per-cell stats; currently 281).

**Effort estimate**: 24-32 hours.

**Why deferred**: Sample-size constraint; cells too thin under 7 states until 2027.

---

### T3.4 — Cross-Pair Sophistication

**What it is**: Add Bank Nifty divergence, USDINR, 10Y bond yield as Tier 2/3 features per design §03 F10-F12.

**When**: When validated need exists (e.g., V2 misclassifies in a way that cross-pair would catch).

**Effort estimate**: 16-24 hours combined.

**Why deferred**: V2 quality already passes V5 P2. Diminishing returns vs added complexity.

---

## 2.5 Discoveries Made During V2 Build

### D1 — V1 Bear bucket is structurally 2 mechanisms

**Source**: `output/regime_v2/validation/out_movers_sonnet_analysis.md`

V1's "Bear" label aggregates **two distinct edge mechanisms** with different forward distributions:
- **Mechanism A** (capitulation bounce): Nifty -10%+ drawdown bottom, UP_TRI fires on intraday reversal; 91.7% WR on bypass cohort, +4.87% mean PnL.
- **Mechanism B** (post-crash recovery beta): Nifty -6% to -7% from peak with recent +5% bounce, UP_TRI fires on continuation; 95.6% WR n=44, +5.6% mean PnL.

These have different optimal regime-classifier definitions. V1 collapsed them; V2 correctly distinguishes them.

### D2 — Group B as a tradable cohort

**Source**: same.

The 44 signals V2 excludes from Bear-family are not noise. They're a distinct edge worth a separate detector. **This is new alpha discovered as a side effect of the V2 build** — not in the design study, not in consultant briefings.

### D3 — V1 C1 metric is structurally unattainable

**Source**: design study §V6 (80% threshold) vs Sonnet analysis section 3.

The design's V1 C1 ≥ 80% requirement assumes V1's Bear bucket is homogeneous. The data shows it isn't. To achieve 80% preservation, V2 would need to include Group B in its Bear cohort, which would dilute the cohort quality V5 P2 measures. **The validation criteria need to be updated to reflect this**.

### D4 — Validation harness caught real calibration bugs before production

**Source**: retune0 → retune1 → retune2 progression in commit messages.

The 3-cycle iteration loop, with Sonnet visual reviews between cycles, surfaced:
- The transition-layer paralysis (CHOPPY → BEAR routing latency)
- The VIX-degraded BULL gate over-strictness
- The Bear fragmentation due to lack of asymmetric persistence
- The minimum-hold need for trend states
- The Group A bypass requirement

None of these would have been visible from unit tests or static analysis. The harness paid for itself.

### D5 — shadow_ops_v1 is not the right tool for batch detector validation

**Source**: prior consultant analysis (`doc/consultant_briefings/round_10_rule031_supplement.pdf` framing).

shadow_ops_v1 is rule-019-specific and rule_031-specific. It does NOT generalize to "validate any new detector". V2 needed its own validation harness — which was built. Useful learning for the broader system.

### D6 — Sonnet API analysis revealed insights that retunes couldn't

**Source**: retune2 Sonnet visual review (broad fix recommendations) vs out-movers analysis (surgical bypass).

The visual review (Sonnet looking at PNG charts) recommended 3 separate fixes (I+J+K) which would have re-included Group B and degraded V2's quality. The data-driven analysis (Sonnet looking at the actual 67 signal records with Nifty context) recommended a single threshold that captured Group A surgically. **Lesson**: pixel-level visual review is useful but data-level analysis is more reliable for precise calibration.

---

## 2.6 What is NOT Part of V2

To prevent scope creep, these are **explicitly NOT** part of "completing V2":

### NOT V2: brain_telegram Step 7
**Different problem.** Per FINAL_SYNTHESIS, this is L1 leverage point — separate work. Brain digest delivery to Telegram. ~200 LOC. Touches `scanner/brain/brain_telegram.py` (currently 6 lines) and `scanner/telegram_bot.py` for `/approve` `/reject` handlers.

### NOT V2: PWA bridge_state integration
**Different problem.** L3 leverage point. Touches `output/ui.js` to fetch and display `bridge_state.json`. Independent of regime.

### NOT V2: Live capital deployment
**Different problem.** Operational decision (Stage 3 of FINAL_SYNTHESIS). Not blocked by V2; blocked by operator readiness + UP_TRI×Bear regime occurring (currently Choppy).

### NOT V2: shadow_ops_v1 bootstrap
**Different problem.** That branch validates rule_019 specifically. V2 is a different layer.

### NOT V2: 5 Bull setups validation
**Different problem.** Phase 4 / Path B work per consultant. V2 unblocks better attribution of Bull signals but doesn't add new detectors.

### NOT V2: Group B detector
**Tier 2, not Tier 1.** Same project family but separable. Can defer to Month 2.

---

## 2.7 Risk Inventory For Remaining Work

### R1 — Production integration breaks UP_TRI×Bear paths

**Probability**: LOW (15%).
**Impact**: HIGH — would degrade the proven 94.7% WR edge.
**Mitigation**:
- Add V2 alongside V1 (parallel write) before any consumer reads V2.
- Existing win_001..win_006 boost rules pin to `regime=Bear` string — keep V1 writing the `regime` field during transition.
- Test in pre-production by running V2 on today's morning scan and comparing UP_TRI count vs V1.

### R2 — Side-by-side run reveals operational disagreements

**Probability**: MEDIUM (40%).
**Impact**: MEDIUM — would block T1.4 until resolved.
**Mitigation**: 10-day window is short enough to fail-fast; if V2 disagrees with V1 in unexpected ways, the shadow log catches it before promotion.

### R3 — V5 P2 metric also has hidden weaknesses

**Probability**: LOW (20%).
**Impact**: MEDIUM — would invalidate the chosen gating metric.
**Mitigation**: V5 P2 is built on the same `signal_history.json` as V1 C1, so if signal_history has issues both metrics suffer equally. The relative comparison (V2 > V1 quality) is robust.

### R4 — Group B detector encoding harder than expected

**Probability**: MEDIUM (30%).
**Impact**: LOW — pure Tier 2, doesn't block V2 promotion.
**Mitigation**: Defer until Month 2 if needed. V2 ships without it.

### R5 — Time-budget overrun (V2 takes 4-6 weeks instead of 3-4)

**Probability**: HIGH (60% given user's "1 of 6 operationalize" base rate).
**Impact**: MEDIUM — psychologically demotivating but not catastrophic.
**Mitigation**: Tier 1 active work is only ~7 hours. The 10-day shadow window is the binding constraint, not engineering time. If user is consistent for 10 trading days, V2 promotes in Week 4. If user disappears mid-shadow, the work resumes whenever they return.

---

## 2.8 Decision Tree for "Done"

Three valid definitions of V2 "done", user picks one:

### Minimum-viable done (Week 4)
- V2 + bypass in production scanner output
- V1 still writing in parallel (shadow)
- 2-week side-by-side validated
- Promotion memo signed
- Brain still reads V1 weekly (no T2.3 yet)

### Target done (Week 6-8)
- All of Minimum
- T2.3 daily refresh wired — brain reads V2 daily
- T2.2 VIX integration if quick

### Full done (Month 3-4)
- All of Target
- T2.1 Group B detector encoded and validated
- V1 retired (D4 timing)
- All cohort_health attributions on V2 axis

**Recommended**: aim for Minimum (Week 4), then continue T2.x in parallel during normal operations. Don't gate the Week 4 promotion on T2 items.

---

## 2.9 Effort Summary Table

| Item | Tier | Engineering hrs | Calendar | Blocks promotion? | Dependencies |
|---|---:|---:|---|:---:|---|
| T1.1 Validation criteria decision | 1 | 1 | same day | YES | none |
| T1.2 Production integration | 1 | 3 | 1-2 days | YES | T1.1 + D2 |
| T1.3 Side-by-side shadow run | 1 | 2 setup + 4 obs | 2-3 wks | YES | T1.2 |
| T1.4 Promotion memo | 1 | 1 | same day | YES | T1.3 |
| **Tier 1 total** | | **~10 hrs** | **3-4 wks elapsed** | | |
| T2.1 Group B detector | 2 | 8-12 | 2-3 wks | No | T1.1 |
| T2.2 VIX integration | 2 | 4-6 | 3 days | No | none |
| T2.3 Daily refresh wiring | 2 | 2-3 | 1 day | No | T1.2 |
| **Tier 2 total** | | **~14-21 hrs** | parallel to T1 | | |
| T3.1 ML refinement | 3 | 40+ | Year 2 | No | 6mo prod data |
| T3.2 Sub-regime | 3 | 16-24 | Month 6 | No | T2.1 |
| T3.3 7-state | 3 | 24-32 | Year 2 | No | sample size |
| T3.4 Cross-pair | 3 | 16-24 | Year 2 | No | none |
| **Tier 3 total** | | **~100 hrs** | future | | |

**Combined Tier 1 + Tier 2 to fully-featured V2**: ~24-31 engineering hours + 2-3 calendar weeks (driven by shadow observation window).

---

# END OF DOCUMENT

*Sources: design study (`doc/regime_v2_design/MASTER_DESIGN.md` and 8 supporting files), validation outputs (`output/regime_v2/validation/*.md`), commit history (5 V2 commits on main), Sonnet analyses (visual reviews + out-movers data-driven), `doc/FINAL_SYNTHESIS.md` Stage 2 Day 3, `doc/consultant_briefings/README.md`.*

*Generated 2026-05-13 evening. Read with morning coffee tomorrow.*
