# Lab Findings Log

**Last updated:** 2026-05-01

This is the canonical persistent log of all Lab findings. Companion to
`DECISIONS_LOG.md` (pending decisions + verdict ledger). Individual
investigation findings live in `lab/analyses/INV-NNN_findings.md`; this file
is the cross-investigation ledger.

---

## Investigation results

### MS-1 cloud fetch + extension
- **Coverage:** 97.46% (192 OK / 5 PARTIAL / 0 FAILED)
- **Universe:** 197 symbols (188 stocks + 9 indices including 7 sector indices Caveat 1 backfill)
- **Date span:** 2011-01 to 2026-04 (15+ years)
- **Status:** COMPLETED
- **Commit chain:** `eb143de9` (initial 2-index cache populated) → `160bb5d9` (`_INDEX_SYMBOLS` extended to 9) → `999b950e` (Caveat 1 backfill consumed by MS-3)

### MS-2 signal regen (post-Caveat 1)
- **Signals:** 105,987 across 15-year backtest
- **Cross-validation:** 90.69% match vs live `signal_history` Apr 2026
- **T2 tripwire:** PASSED
- **Status:** COMPLETED
- **Commit:** `f26b4c22`

### MS-3 regime classifier replay (post-Caveat 1)
- **Regimes:** 3757 days classified (Bear / Bull / Choppy)
- **Sector momentum:** Real Leading / Lagging values for all 8 indexed sectors (post-Caveat 1)
- **T3 tripwire:** PASSED (Apr 17 + Apr 29 confirmed Choppy)
- **Status:** COMPLETED
- **Commit:** `999b950e`

### MS-4 hypothesis_tester hardening (3 bugs caught + fixed)
- **Block 1:** Wilson + p-value gates not enforced → fixed (commit `8e1c2e94`)
- **Block 2:** FILTER routing ambiguity → fixed (commit `d5dfc9ac`)
- **Block 3:** FP-precision bug at tier boundaries → fixed via `round(..., 4)` (commit `6e80644d`)
- **Tests:** 41/41 passing
- **Status:** COMPLETED

### INV-001 — UP_TRI × Bank × Choppy structural failure
- **Lifetime cohort:** n=5146 resolved, WR 52.14%
- **Train→Test drift:** 6.52pp
- **Mechanism candidates (6):** all INCONCLUSIVE (PSU/Private, vol_q, Bank Nifty 20d momentum, time-of-month, signal score, calendar proximity)
- **Inverse patterns (3):** all NO_INVERSE_SIGNAL (DOWN_TRI same dates, defensive sector rotation, BULL_PROXY post-failure)
- **Parent KILL tier:** REJECT
- **GTB-002 validation:** GATE_4_PASS (kill_002 prevents 14L, suppresses 2W, ratio 7.0)
- **Year-over-year:** 2026 YTD WR 39% (worst year in 15-year history); 4-year declining trend (60→52→52→45→39)
- **Verdict:** Lab tier REJECT for structural KILL; Apr 2026 cluster identified as outlier event
- **Status:** COMPLETED (patterns.json status update pending in BLOCK 2)
- **Caveat 2 impact:** minimal at lifetime n=5146
- **Findings:** `lab/analyses/INV-001_findings.md`

### INV-002 — UP_TRI × Bank × Bear validation
- **Lifetime cohort:** n=2689 resolved, WR 52.83%
- **Bear sub-periods identified:** 29
- **Parent BOOST tier:** REJECT
- **HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT:** sub-period WR range 10%-83% confirms live n=8 100% WR sample-window artifact
- **Section 2b CANDIDATE:** Bank Nifty 60d return — 28.26pp Δ WR; negative-60d 55.7% vs positive-60d 27.4%; p<0.001
- **2021_Bear_11 outlier:** 124 signals at 10.34% WR (single sub-period dragging lifetime stat)
- **Verdict:** Lab parent BOOST tier REJECT; Section 2b filter is real but doesn't catch Apr cluster (Phase 4 verified)
- **Status:** COMPLETED (patterns.json status update pending in BLOCK 2)
- **Findings:** `lab/analyses/INV-002_findings.md`

### Phase 4 — Apr 2026 cluster verification (against Section 2b filter)
- **Apr cluster signals:** 70 Bank UP_TRI signals (Apr 17-21 window)
- **Distribution:** All 70 in negative-60d Bank Nifty subset (the "good" subset per Section 2b)
- **Apr WR:** 27% (matches live n=26 WR 27%)
- **kill_002_v2 counterfactual:** would have caught 0 of 70 losses
- **Verdict:** Section 2b filter does NOT explain Apr cluster; Apr appears one-time outlier event, not structural pattern
- **Status:** COMPLETED

### INV-003 — 117-cohort discovery scan
- **Cohorts evaluated:** 117 (13 sectors × 3 regimes × 3 signals)
- **Tier S patterns:** 0
- **Tier A patterns:** 0
- **Tier B patterns:** 7 (3 boost + 4 kill)
- **REJECT:** 106
- **INSUFFICIENT_N:** 4

**Tier B boost candidates (3):**
- Pharma × Bull × BULL_PROXY (n=161, drift 8.4pp)
- CapGoods × Bear × UP_TRI (n=754, drift 4.9pp)
- Chem × Bear × UP_TRI (n=938, drift 7.3pp)

**Tier B kill candidates (4):**
- Other × Bear × BULL_PROXY (n=35; Caveat 2 vulnerable)
- Infra × Choppy × BULL_PROXY (n=129)
- FMCG × Bull × DOWN_TRI (n=625)
- Energy × Bear × DOWN_TRI (n=243)

- **Cross-validation:** INV-001 + INV-002 cells reproduced (both REJECT confirms standalone)
- **Status:** COMPLETED (patterns.json status update pending in BLOCK 2)
- **Findings:** `lab/analyses/INV-003_findings.md`

### INV-006 — Exit timing optimization
- **Variants tested:** 12 (D2-D10 fixed-day + 3 ATR trailing stops + 2 profit ladders) × 3 signal types
- **Total evaluations:** 105,415

**WR-only conclusion:** D6 confirmed competitive; 0 variants beat at 3pp + p<0.05 threshold

**Supplementary pnl analysis:**
- **UP_TRI × D10:** +82.7% pnl improvement, p<0.001 — VALID
- **BULL_PROXY × D10:** +43.7% pnl improvement, p=0.035 — VALID
- **DOWN_TRI × D10:** +50% pnl reported — INVALID (runner LONG-only bug)

**Drawdown + capital efficiency analysis:**
- **UP_TRI × D10:** plausibly net positive (+16% capital efficiency, but 2pp deeper p5 tail)
- **BULL_PROXY × D10:** net negative (-6% capital efficiency); stay D6
- **DOWN_TRI:** UNKNOWN (runner bug invalidates analysis)

**Runner bug audit (separate session):**
- Live scanner DOWN_TRI handling: CORRECT
- Backtest signal_replayer DOWN_TRI handling: CORRECT
- INV-006 runner DOWN_TRI handling: BUGGED (LONG-only pnl + stop logic)
- **No production fix required**
- **INV-001/002/003 unaffected** (used `hypothesis_tester` direct on `backtest_signals.outcome`, bypassing runner)

- **Status:** COMPLETED for UP_TRI + BULL_PROXY; DOWN_TRI deferred to INV-013 (patterns.json status update pending in BLOCK 2)
- **Findings:** `lab/analyses/INV-006_findings.md`
- **Findings banner committed:** `58ccf85e`

---

## Pending decisions

See `lab/DECISIONS_LOG.md` for full ledger. Headline pending items:

1. kill_002 ship path (NO SHIP recommended per Lab Discipline Principle 6)
2. INV-001/002/003/006 patterns.json status updates → COMPLETED (executing in BLOCK 2)
3. UP_TRI HOLDING_DAYS migration to D10 (defer until INV-007/010/012 complete; batch decision)
4. 7 Tier B candidates from INV-003 — individual review (defer to dedicated session)
5. Caveat 2 audit (9.31% MS-2 miss-rate)

---

## Cross-INV synthesis observations

- All Lab cohorts in current signal universe (UP_TRI / DOWN_TRI / BULL_PROXY × 11 sectors × 3 regimes) max out at Tier B
- 0 Tier S or A patterns surfaced across 117-cohort scan + parent INV-001 / INV-002 cohorts
- Lifetime WR ~52% across signals matches live signal calibration (signals are real but noisy)
- D6 exit confirmed strong baseline; D10 candidate for UP_TRI specifically (+16% capital efficiency, -2pp deeper p5 tail)
- Apr 2026 cluster appears outlier event, not structural pattern — Phase 4 verification ruled out the Section 2b filter as explanation
- Bank cohorts (UP_TRI × Bank in Bear / Choppy) both REJECT — informational about Bank tradeability in current regimes
- Discovery investigations INV-007 / INV-010 / INV-012 still pre-registered awaiting execution sessions
