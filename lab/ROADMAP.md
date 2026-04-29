# Backtest Lab Roadmap

**Purpose:** Plan + sequence Lab work. Investigation queue, infrastructure build milestones, and cohort sweep schedule. This is a living document; revised as investigations complete and new evidence surfaces.

**Companion docs:** `README.md` (vision); `PROMOTION_PROTOCOL.md` (7-gate pipeline + tier structure).

**Founding date:** 2026-04-30.

---

## Investigation Queue

Investigations are filed as Lab work items. Each investigation is its own multi-session effort — typical scope 8-20 hours of focused analytical work plus infrastructure prerequisites. Listed in priority order; priority can shift as new loss batches surface or live cohort drift triggers re-investigation.

**ROADMAP vs `patterns.json` registry — intentional asymmetry.** This ROADMAP lists ALL planned investigations (including INV-004 deferred-registration). The `patterns.json` registry contains only investigations whose hypotheses are formally pre-registered with concrete thresholds and methodology — this is what `PROMOTION_PROTOCOL.md` Gate 1 requires. Investigations whose threshold specifics depend on findings from a prior investigation (INV-004 needs INV-001 mechanism analysis to inform volume thresholds) are NOT pre-registered until those findings exist; pre-registering them prematurely would be fitting hypothesis to forthcoming evidence (post-hoc disguised as pre-registration). The asymmetry is OOS discipline, not oversight.

---

### INV-001 — UP_TRI × Bank × Choppy structural failure deep-dive

**Priority:** HIGH (founding investigation; motivated Lab founding)

**Trigger:** Apr 17 + Apr 29 cluster losses; live cohort **n=26 resolved (+ 3 OPEN), WR 27%** confirmed structural pattern in 4-week sample. Today's 17 Bank resolutions are a SUBSET of the 26 lifetime resolved (not additive). kill_002 ships as `LIVE_EVIDENCE_ONLY` on main pending Lab validation; live n=26 is below Lab tier minimums (Tier A: n≥50; Tier B: n≥30), so investigation expands to historical n via 15-year backtest replay.

**Hypothesis (primary):** UP_TRI breakouts in Bank sector during Choppy regime fail because of [mechanism TBD]. Initial candidate mechanisms (investigation may surface others):
1. Sector-internal churn — rate-sensitive flows + index rebalancing absorbing breakout momentum
2. Sub-sector heterogeneity — PSU banks behaving differently from private banks
3. Macro-window proximity — RBI policy / Bank earnings windows distort cohort (e.g., ±3 trading days)
4. Volume-divergence — weak-volume breakouts are retail-driven, no institutional follow-through

Investigation tests these candidates plus any additional mechanisms surfaced during Phase 3 cohort comparison (LOSER vs WINNER differentiator analysis).

**Hypothesis (inverse):** On dates when UP_TRI × Bank × Choppy fails, [pattern TBD] profits. Initial candidate inverse patterns (investigation may surface others):
1. DOWN_TRI × Bank × Choppy on same dates — does shorting the same stocks work?
2. UP_TRI × defensive sectors (Pharma / Energy / FMCG) on same Choppy days — does sector rotation profit?
3. BULL_PROXY (mean-reversion) on same Bank stocks 2-3 days post-failed-breakout — does fade-the-failed-breakout work?

Investigation tests these candidates plus any additional inverse patterns surfaced during Phase 3 cross-cohort analysis (which cohort profited on dates when UP_TRI × Bank × Choppy failed).

**Methodology:** 15-year historical backtest (2011-01 → 2026-04); cohort baseline; mechanism analysis (8 differentiators per `PROMOTION_PROTOCOL.md` Gate 5 examples); inverse-pattern search (7 INV-1..INV-7 candidates per founding session sketch); train/test OOS validation; ground-truth validation against `/lab/registry/ground_truth_batches/GTB-001.json` + `GTB-002.json`.

**Estimated effort:** 12-20 hours across 4-7 sessions.

**Status:** Pre-registered in `/lab/registry/patterns.json`. Investigation starts when MS-1..MS-4 infrastructure ready.

**Dependencies:** MS-1 (data fetch) + MS-2 (signal regen) + MS-3 (regime replay) + MS-4 (hypothesis tester).

**Expected outcomes (3 paths):**
- (a) Structural failure confirmed + mechanism articulated → kill_002 re-promoted to Lab Tier A or S kill (replacing current `LIVE_EVIDENCE_ONLY` tag)
- (b) Sub-cohort filter found → kill_002 narrowed to specific Bank sub-sectors; remaining sub-cohorts promoted to boost
- (c) Recent-regime artifact → kill_002 remains as live operational rule but does NOT earn Lab tier; investigation pivots to regime classifier review

---

### INV-002 — UP_TRI × Bank × Bear validation (small-sample hypothesis)

**Priority:** HIGH (suspicious 100% WR n=8; needs historical validation before tier assignment)

**Trigger:** Live data shows UP_TRI × Bank × Bear at n=8 W=8 L=0 → 100% WR. Sharply opposite to UP_TRI × Bank × Choppy at WR 27%. Suspiciously perfect; verify on 15-year history before any Tier S boost promotion.

**Hypothesis (primary):** Cohort genuinely profits in Bear regime due to [mechanism TBD]; n=8 is real signal not statistical artifact. Candidate mechanisms:
- Bank stocks oversold during Bear macro; defensive rebound on any breakout signal
- Rate-cycle correlation (Bear regime often coincides with rate-cut expectations → bank-positive)
- Sample-window bias (Apr 2026 Bear regime was specific 9-day window; cohort may not generalize)

**Methodology:** Backtest infrastructure same as INV-001; cohort baseline 15 years; mechanism analysis; OOS validation. Specifically test for sample-window bias: split historical Bear regimes by sub-period and verify WR holds across multiple Bear episodes (2013, 2016, 2018, 2020, 2022).

**Estimated effort:** 4-8 hours.

**Status:** Pre-registered.

**Dependencies:** Same as INV-001 (MS-1..MS-4).

**Expected outcomes:**
- (a) Historical confirmation across multiple Bear episodes → high-confidence Tier S boost (UP_TRI × Bank × Bear with `conviction_tag: "HIGH"`)
- (b) Recent-regime artifact (Apr 2026 Bear was special) → Tier B watch only; flag for re-investigation when next genuine Bear regime arrives
- (c) Statistical small-sample noise → reject; document; require larger sample before re-investigation

---

### INV-003 — Sector × regime × signal profitability matrix

**Priority:** MEDIUM (broad discovery scan; informs INV-004+ hypothesis generation)

**Trigger:** Lab discovery question. Beyond specific cohorts, surface the FULL matrix of profitable / unprofitable cohort triples to identify tradeable structure systematically.

**Hypothesis:** Some sector × regime × signal triples are reliably profitable; others reliably unprofitable. The matrix surfaces tradeable structure not visible from individual investigations.

**Methodology:** Backtest-driven matrix population. For each (signal_type ∈ {UP_TRI, DOWN_TRI, BULL_PROXY}) × (sector ∈ 11 sectors) × (regime ∈ {Bear, Choppy, Bull}) = **99 cohort triples**, compute backtest baseline statistics (n, W, L, F, WR, avg pnl, Sharpe, max drawdown). Apply train/test OOS protocol; rank cohorts by tier eligibility per `PROMOTION_PROTOCOL.md` Gate 3.

**Estimated effort:** 16-24 hours (plus infrastructure prerequisites).

**Status:** Pre-registered.

**Dependencies:** MS-1..MS-4 + MS-5 (ground-truth validator for established loss batches).

**Expected outcomes:**
- Matrix population: 99 cohorts ranked by tier eligibility
- 3-5 high-conviction promotion candidates (Tier A or S boost) identified for individual deeper investigation
- 5-10 kill candidates identified for INV-NN follow-ups
- Heat-map visualization stored in `/lab/analyses/INV-003/cohort_matrix.html` (or similar)

---

### INV-004 — Volume profile filter (post-INV-001 dependent)

**Priority:** MEDIUM (depends on INV-001 mechanism findings)

**Trigger:** Hypothesis from INV-001 mechanism analysis. Volume at signal time may distinguish winners from losers within UP_TRI × Bank × Choppy cohort.

**Hypothesis:** UP_TRI breakouts on > median 50-day volume have meaningfully higher follow-through (≥ 15pp WR delta vs below-median). Mechanism: high volume signals institutional participation; weak-volume breakouts are retail-driven and revert.

**Methodology:** Cross-cohort volume analysis with OOS validation. Within INV-001's UP_TRI × Bank × Choppy cohort, split by volume quintile at signal date; compute per-quintile WR; test whether top-quintile WR meets Tier A/B boost criteria as filter pattern.

**Estimated effort:** 6-10 hours.

**Status:** Will register AFTER INV-001 mechanism findings inform exact thresholds (median volume, lookback window, etc.). Premature registration risks fitting filter to whatever INV-001 surfaces.

**Dependencies:** INV-001 completion + volume data in MS-1 fetched OHLCV.

---

### INV-005 — Macro-window proximity filter (RBI policy / Bank earnings)

**Priority:** LOW (speculative hypothesis; lower investigation priority)

**Trigger:** Hypothesis. RBI policy days, Bank earnings announcements may distort cohort behavior. Worth testing once core investigations settle.

**Hypothesis:** UP_TRI × Bank × Choppy within ±3 trading days of RBI MPC announcement fails more than baseline. Mechanism: macro uncertainty around policy decisions distorts technical breakout follow-through.

**Methodology:** Calendar-event tagged backtest. RBI MPC dates pulled from public calendar (8 meetings/year); Bank earnings announcement dates from corporate filings. Tag every UP_TRI × Bank × Choppy signal with `macro_proximity_days` field; split cohort by proximity bucket; test for WR variance.

**Estimated effort:** 8-12 hours (data sourcing for macro calendar adds time).

**Status:** Pre-registered as low-priority. Likely won't execute until INV-001..INV-004 complete.

**Dependencies:** MS-1..MS-4 + RBI/earnings calendar data sourcing (manual download protocol).

---

## Lab Infrastructure Build Plan

Before INV-001 can execute, foundational infrastructure must be built. These are milestone deliverables, each its own multi-session effort.

### MS-1: Data layer (~4-6 hours)

**Goal:** Fetch + cache 15-year OHLCV data for 188 F&O stocks plus index data.

**Files:**
- `/lab/infrastructure/data_fetcher.py` — yfinance primary + retry/backoff (3x exponential) + NSE bhav copy fallback (manual download protocol documented)
- `/lab/cache/{symbol}.parquet` — per-stock cached OHLCV
- `/lab/cache/_index_NSEI.parquet`, `_index_NSEBANK.parquet`, etc. — index data
- `/lab/logs/fetch_report.json` — per-symbol fetch status + missing date list

**Coverage tolerance:** Minimum 70% universe coverage; flag missing symbols; document survivorship-bias caveat in fetch_report.

**Validation:** Cross-check 5 random stocks against external source (e.g., NSE direct download for spot-validation).

**Resume capability:** Skip already-cached unless `--refetch` flag.

---

### MS-2: Signal regeneration (~4-6 hours)

**Goal:** Replay UP_TRI / DOWN_TRI / BULL_PROXY signal detection on historical OHLC.

**Files:**
- `/lab/infrastructure/signal_replayer.py` — pure-function detectors against historical OHLC
- `/lab/output/backtest_signals.parquet` — full schema: [stock, signal_date, signal_type, sector, regime, score, entry_price, stop_price, exit_date, exit_price, exit_reason, pnl_pct, outcome]

**Validation:** Cross-reference regenerated signals (filtered to 2026-04) vs `output/signal_history.json` 2026-04 entries on `(stock, signal_date, signal_type, outcome)` tuple. **80% match required**; below threshold halts pipeline (regeneration has bug).

**Edge cases handled:** Stop-hit detection during 5-day holding window (intraday low < stop_price → STOP exit at that day); pivot detection on historical data with appropriate lookback windows; second-attempt (SA) signal logic if scope creeps.

---

### MS-3: Regime classifier replay (~3-5 hours)

**Goal:** Apply live regime classifier to historical Nifty data; output per-day regime labels for 15-year period.

**Files:**
- `/lab/infrastructure/regime_replayer.py` — pure-function classifier on arbitrary Nifty OHLC
- `/lab/output/regime_history.parquet` — schema: [date, regime, classifier_inputs]

**Critical prerequisite:** Live regime classifier must be callable as pure function on arbitrary historical data. If not (TBD via audit during MS-3 build), refactor scope opens (~1 hr extra) OR fallback to hardcoded regime-by-date table from live history + Nifty volatility heuristic for pre-live period.

**Validation:** Replay must yield "Choppy" label for 2026-04-17 + 2026-04-29 (matches live classifier behavior on those dates). Below this floor halts pipeline (classifier replay has bug).

**Caveat acknowledged in output:** Classifier calibrated on 2025-2026 data; older regime labels (2008-2015) approximate per `README.md` discipline principle 3.

---

### MS-4: Pattern testing harness (~2-3 hours)

**Goal:** Train/test split + WR + Wilson + p-value computation per `PROMOTION_PROTOCOL.md` Gate 3 thresholds.

**Files:**
- `/lab/infrastructure/hypothesis_tester.py` — input cohort filter + train period + test period; output tier eligibility verdict per `PROMOTION_PROTOCOL.md` thresholds

**API:**
```python
test_hypothesis(
    backtest_signals_df,
    cohort_filter={"signal": "UP_TRI", "sector": "Bank", "regime": "Choppy"},
    train_period=("2011-01-01", "2022-12-31"),
    test_period=("2023-01-01", "2026-04-30"),
    pattern_type="kill",  # or "boost" or "filter"
) → {tier_landing: "Tier A kill" | None, train_stats, test_stats, drift_pp, wilson, p_value}
```

**Validation:** Run on synthetic cohort with known WR; verify thresholds fire correctly.

---

### MS-5: Ground-truth validator (~2-3 hours)

**Goal:** Replay patterns against `/lab/registry/ground_truth_batches/` loss batches; compute counterfactual P&L per `PROMOTION_PROTOCOL.md` Gate 4.

**Files:**
- `/lab/infrastructure/ground_truth_validator.py` — input pattern + ground-truth batch ID; output prevented losses + suppressed winners + net P&L delta

**API:**
```python
validate_against_ground_truth(
    pattern_def,  # the kill/boost rule being tested
    ground_truth_batch_ids=["GTB-001", "GTB-002"],
) → {prevented_losses_pnl, suppressed_winners_pnl, net_delta_pct, batch_breakdown}
```

**Validation:** Apply known kill_002 (UP_TRI × Bank × Choppy) to GTB-002 (Apr 29 batch); verify prevented-losses count matches the 14 losses in GTB-002.

---

**Total infrastructure build:** 15-23 hours across 5 milestones, multiple sessions.

**Sequence:** MS-1 → MS-2 → MS-3 → MS-4 → MS-5. INV-001 + INV-002 require MS-1..MS-4. INV-003 also requires MS-5.

---

## Cohort Sweep Schedule

In addition to per-investigation work, Lab runs recurring sweeps to surface emerging patterns and detect drift in promoted patterns.

### Weekly: Live cohort drift report

**Cadence:** Sunday evening; output `/lab/analyses/weekly_drift_report_<date>.md`.

**Content:**
- Compare past 7 days of live `signal_history.json` vs historical lifetime baseline per cohort.
- Flag cohorts with WR drift > tier-specific bound (10pp Tier S / 15pp Tier A / 20pp Tier B per `PROMOTION_PROTOCOL.md` Gate 3).
- Trigger investigation INV-NNN if any flagged cohort is currently a promoted pattern.

**Time:** ~1 hour per sweep (largely automated once MS-1..MS-4 ready).

### Monthly: New pattern discovery scan

**Cadence:** First Sunday of each month; output `/lab/analyses/monthly_discovery_<YYYY-MM>.md`.

**Content:**
- Re-run INV-003 cohort-matrix output with newly available month of data.
- Surface emerging patterns (new high-conviction tier candidates that weren't visible last month).
- Pre-register as new INV-NN if any pattern crosses Tier B floor.

**Time:** ~2-3 hours per sweep.

### Quarterly: Regime classifier review

**Cadence:** First Sunday of each calendar quarter; output `/lab/analyses/quarterly_classifier_review_<YYYY-QN>.md`.

**Content:**
- Test classifier consistency across last 3 months: does live label match what backtest replay would produce on the same Nifty data?
- If drift detected (e.g., classifier label flips on >10% of recent days under same input data): open investigation INV-XXX (regime classifier refactor candidate).

**Time:** ~2-3 hours per review.

---

## Roadmap Discipline Notes

1. **Priority can shift.** A new live loss batch may bump a low-priority investigation to top of queue.
2. **Investigations don't block each other.** INV-001 and INV-002 share infrastructure (MS-1..MS-4) but are independent investigations; INV-002 can complete first if simpler.
3. **Sweeps are not optional.** Weekly drift report runs even when no investigation is active. Promoted patterns degrade silently otherwise.
4. **New investigations must be pre-registered.** Per `PROMOTION_PROTOCOL.md` Gate 1, hypothesis registration in `patterns.json` predates backtest run. ROADMAP entries are themselves pre-registration of intent.
5. **Sequence flex.** MS-1 → MS-2 is hard ordering; MS-3 + MS-4 + MS-5 can build in parallel if multiple sessions available.
