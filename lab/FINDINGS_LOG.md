# Lab Findings Log

**Last updated:** 2026-05-04

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

### INV-007 — Volatility regime filter discovery
- **Cohorts evaluated:** 9 cells (3 signals × 3 vol buckets: Low/Medium/High)
- **Vol definition:** Nifty 20-day rolling realized vol × √252; bucket thresholds p30=0.1082, p70=0.1604 (15-yr distribution)
- **Bucket day counts:** Low 1121 / Medium 1494 / High 1121

**Unfiltered baselines (vol-NaN signals excluded; 761 dropped of 105987):**
- UP_TRI: n=71248, WR 0.5283
- DOWN_TRI: n=17751, WR 0.4474
- BULL_PROXY: n=4965, WR 0.5003

**Surfaces found:**
- CANDIDATE: 0 (none cleared |Δ WR| ≥ 5pp + p<0.05 + n≥100)
- MARGINAL: 1 (BULL_PROXY × Medium −2.02pp; below CANDIDATE threshold but directional)
- NO_EDGE: 8

**Tier-earning cells (BOOST or KILL S/A/B):** 0 — all 9 cells reach REJECT on both hypothesis types

**Cross-bucket avg Δ WR:**
- Low: −0.07pp (signal-specific; signs vary)
- Medium: −0.74pp (signal-specific)
- High: +1.22pp (signal-specific; magnitude <2pp)

**Largest single-cell deltas:**
- BULL_PROXY × High +3.29pp (above baseline; below CANDIDATE threshold)
- BULL_PROXY × Medium −2.02pp (MARGINAL)
- UP_TRI × High +1.28pp
- DOWN_TRI × High −0.91pp

**Headline finding:** Vol regime filter does not yield clear edge in current universe. No filter promotion candidates surfaced; vol regime adds no statistically significant differentiation to UP_TRI / DOWN_TRI / BULL_PROXY signals in 15-year backtest.

**Caveats:**
- Vol warm-up exclusion: 20 days dropped (761 signals, 0.72% of universe)
- Caveat 2 (9.31% MS-2 miss-rate) inherited but unlikely to swing verdict given uniform NO_EDGE across cells
- Direction handling correct: hypothesis_tester.evaluate_hypothesis used exclusively (no LONG-only manual recomputation; INV-006 runner bug pattern avoided)

- **Status:** COMPLETED (patterns.json status update pending user review)
- **Findings:** `lab/analyses/INV-007_findings.md`
- **Pending decision:** review filter surfaces; decide if any warrant filter implementation (recommended: NONE — verdict NO_EDGE)

### INV-013 — DOWN_TRI exit timing direction-aware
- **Variants tested:** 12 (D2-D10 + 3 ATR trail + 2 profit ladders)
- **Total DOWN_TRI signals:** 19961 (all direction=SHORT verified); 13 skipped (cohort-end edge)
- **Direction-aware fix:** SHORT semantics applied (validates against INV-006 LONG-only runner bug); Section 4 inversion verification — D6 sum INV-006+INV-013 = 1.0000 EXACT

**D6 baseline (SHORT-direction, corrected):**
- WR: 0.4653, n_excl_flat: 18097, Wilson: 0.4581
- avg_pnl: **-0.6072% (NEGATIVE)** — DOWN_TRI structurally loses at D6
- R-mult: -0.1596

**Variants BEAT D6 on WR (≥3pp + p<0.05 + n≥100):** 0 (matches INV-006 LONG cohorts pattern)

**Variants WORSE on WR:** 5 — all trailing stops + both ladders

**Variants BEAT D6 on pnl (≥10% relative + p<0.05):** 6
- D2: -0.203% (vs D6 -0.607%; rel +66.5%; p<0.0001) — strongest
- D3: -0.269% rel +55.7%
- D4: -0.376% rel +38.1%
- D5: -0.496% rel +18.3%; p=0.038
- TRAIL_1.5xATR: -0.454% rel +25.2%
- LADDER_B_33_33_34trailing: -0.354% rel +41.8%

**Critical finding — opposite direction from UP_TRI/BULL_PROXY:**
- LONG signals: LONGER holds (D10) beat D6 on pnl (let winners run)
- SHORT signals: SHORTER holds (D2-D5) beat D6 on pnl (cut early before mean reversion against trend)

DOWN_TRI cohort is structurally challenged (consistent with Indian equity bull bias 2011-2026); "improvements" reduce loss (less negative pnl) rather than producing positive pnl. Even D2 still loses -0.203% per trade on average.

**Headline finding:** INV-013 finds 0 variants beating D6 on WR but 6 beating on pnl. Strongest is D2 at +66.5% relative pnl improvement. Pattern parallels INV-006 UP_TRI/BULL_PROXY where direction matters but inverts: LONG = let winners run; SHORT = cut early.

**INV-006 inversion verification (Section 4):**
- D6 INV-006 reported: 0.5347 (INVALID — LONG-direction)
- D6 INV-013 corrected: 0.4653 (SHORT-direction)
- Sum: 1.0000 EXACT — clean LONG/SHORT W/L inversion confirmed
- Trailing/ladder sums diverge from 1.0 because stop placement differs (above vs below entry); not pure sign-flip

**Caveats:**
- Caveat 2 (9.31% MS-2 miss-rate) inherited; surfaced D2-D5 candidates need Caveat 2 audit before promotion
- ATR NaN for first 14 days of cache; ATR-based variants flagged ATR_UNAVAILABLE for those signals
- Direction-aware fix is the primary methodology change; runner code in inv_013_runner.py (NOT modified inv_006_runner.py per scope)

- **Status:** COMPLETED (patterns.json status update pending user review)
- **Findings:** `lab/analyses/INV-013_findings.md`
- **Pending decision:** review DOWN_TRI exit migration candidate (D2 strongest); cross-reference with INV-006 UP_TRI D10 finding for unified scanner.config decision (signal-specific exits required: D10 for LONG, D2-D3 for SHORT)

### INV-010 — GAP_BREAKOUT new entry signal discovery
- **Detection:** n=1827 signals across 183 of 188 F&O stocks × 15-year backtest (1.05s runtime); 0 stocks skipped
- **Signal definition:** LONG; gap-up >0.5% + 5-day high break + prior 10-day consolidation <5% + volume >1.2× 20d avg
- **Entry/exit:** entry=today's close; stop=entry×0.95 (5%); target=entry×1.10 (10%; 2:1 RR); D6 hold

**Lifetime cohort:**
- n_total 1827; n_resolved 1605; n_excl_flat 1605
- WR 0.5371; Wilson lower 0.5126; p-value vs 50%: significant
- avg_pnl per resolved trade: positive but modest

**Tier verdicts (lifetime):**
- BOOST tier: **REJECT** (WR 0.54 below 60% Tier B floor)
- KILL tier: **REJECT** (WR 0.54 above 40% Tier B ceiling)

**Sub-cohort tier hits (4 of 18 OK cells earn Tier B BOOST):**
- Bank × Choppy: WR 0.581 (n=74) → BOOST B — *same cohort INV-001 REJECTed for UP_TRI; new signal type performs differently*
- FMCG × Choppy: WR 0.582 (n=67) → BOOST B
- FMCG × Bull: WR 0.617 (n=128) → BOOST B
- Other × Bull: WR 0.646 (n=65) → BOOST B
- 0 KILL tier hits across all 39 cells (18 OK + 21 INSUFFICIENT_N)

**vs UP_TRI baseline:**
- UP_TRI baseline WR: 0.5281 (n=71865)
- GAP_BREAKOUT WR: 0.5371
- Δ WR: +0.90pp — **MARGINAL/EQUIVALENT** (below 3pp candidate threshold + p<0.05)
- New signal does not materially beat UP_TRI on lifetime WR

**Headline:** GAP_BREAKOUT lifetime cohort REJECTs at parent tier but 4 sub-cohorts earn Tier B BOOST. New signal does not materially beat UP_TRI on lifetime WR (+0.90pp marginal); however 4 sub-cohorts (Bank×Choppy, FMCG×Choppy, FMCG×Bull, Other×Bull) earn tier — conditional GAP_BREAKOUT signal possible if user accepts sub-cohort restriction. Notable that Bank×Choppy earns Tier B for GAP_BREAKOUT despite INV-001 REJECTing same cohort for UP_TRI.

**Caveats:**
- Caveat 2 (9.31% MS-2 miss-rate) — INV-010 builds detector from cache directly so not subject to original miss-rate; cache miss-rate (yfinance gaps) may affect detection at margin
- Sub-cohort n at marginal levels (65-128) — Caveat 2 audit recommended before promotion
- Detector parameters (0.5% gap, 5% range, 1.2× vol) arbitrary; sensitivity analysis available if findings sit near boundaries
- NO live or backtest production fix needed; new signal type would require scanner.scanner_core integration on separate main-branch session

- **Status:** COMPLETED (patterns.json status update pending user review)
- **Findings:** `lab/analyses/INV-010_findings.md`
- **Output:** `lab/output/backtest_signals_INV010.parquet` (1827 rows)
- **Pending decision:** review GAP_BREAKOUT viability — full signal vs conditional sub-cohort signal vs archive

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
- Discovery investigations INV-010 / INV-012 still pre-registered awaiting execution sessions; INV-007 COMPLETED (NO_EDGE verdict)
- Three completed discovery investigations (INV-003 117-cohort, INV-006 exit timing, INV-007 vol filter) all converge on a consistent picture: the current signal universe is statistically near-coin-flip after OOS + drift + Wilson gates; no Tier S/A patterns surface from any direction
- INV-013 (DOWN_TRI direction-aware exit timing) closes the INV-006 runner-bug-fix loop with a structural finding: SHORT signals favor SHORTER holds (D2-D5) — opposite direction from LONG signals (which favor LONGER holds D10). Signal-specific exits required if migration pursued.
- Four completed exit-timing investigations (INV-006 UP_TRI/BULL_PROXY/DOWN_TRI-invalid + INV-013 DOWN_TRI-corrected) now span the full LONG/SHORT space with consistent semantics
- INV-010 (GAP_BREAKOUT new signal) completes — lifetime tier REJECT but 4 sub-cohorts earn Tier B BOOST; reinforces that signal-cohort interaction matters (Bank×Choppy was REJECT for UP_TRI but Tier B for GAP_BREAKOUT). Adds INV-010 to discovery space along with INV-003/006/007/013.
